# Sentinel

Sentinel is an access-control and perimeter-monitoring system. An admin dashboard manages cameras and people; edge camera clients pair with one-time access keys and talk to a Node/Express + MongoDB API.

| Component | Role |
|-----------|------|
| **Admin dashboard** | Create cameras/users, authorize faces, view alerts & notifications |
| **Facial camera** | Viola–Jones crop + InsightFace `buffalo_s` → enroll / recognize |
| **Surveillance camera** | Optical flow + DINOv3 → motion alerts (`human` / `animal` / `unknown object`) |
| **API server** | Auth, pairing, gallery, alerts; also serves the built dashboard |

---

## Architecture

```text
┌─────────────────────┐     cookie JWT      ┌──────────────────────┐
│  Admin dashboard    │◄───────────────────►│  Express API (:3000)  │
│  (React → static/)  │                     │  + MongoDB           │
└─────────────────────┘                     └──────────┬───────────┘
                                                       │
                         camera JWT (Bearer)           │
         ┌───────────────────────────┬─────────────────┘
         ▼                           ▼
┌─────────────────┐         ┌──────────────────────┐
│  facial-cam     │         │  surveillance-cam    │
│  claim / enroll │         │  claim / run         │
│  enroll / run   │         │  10s alert aggregator│
└─────────────────┘         └──────────────────────┘
```

### High-level flows

1. **Camera pairing** — Admin creates a camera → gets a one-time access key → device runs `claim` (or claims on first use) → camera becomes `active` and receives a JWT.
2. **Remote face enroll** — Admin creates a user → gets an enroll key → person enrolls at a facial camera → status `enrolled` → admin **Authorize** → status `authorized` (dashboard notification).
3. **Face recognition** — Facial cam loads enrolled+authorized embeddings from the API; after ~3s continuous match it reports `authorized` or `unauthorized`.
4. **Motion alerts** — Surveillance cam classifies movers; every **10 seconds** it sends **one** aggregated alert (human ≥3% → animal ≥5% → else unknown object).

---

## Repository layout

```text
sentinel/
├── server/                 # Express API + serves dashboard from static/
│   ├── controllers/
│   ├── middleware/         # adminAuth (cookie), cameraAuth (Bearer)
│   ├── models/             # Camera, User, Alert, Notification
│   ├── routes/
│   ├── utils/keys.js       # one-time access / enroll keys
│   ├── static/             # built React UI (gitignored; run build:ui)
│   ├── .env                # secrets (gitignored)
│   └── index.js
├── frontend/               # React + Vite source (builds into server/static)
├── cameras/
│   ├── common/             # shared HTTP client + prompts
│   ├── facial-cam/         # face enroll / recognize
│   ├── surveillance-cam/   # optical flow + DINOv3 + alert aggregation
│   ├── data/               # Haar cascade + optional offline face gallery
│   ├── videos/             # sample clips for local testing
│   └── .tokens/            # saved camera JWTs (gitignored)
└── README.md
```

---

## Prerequisites

- **Node.js** 18+ (API + dashboard build)
- **MongoDB** running locally (default `mongodb://localhost:27017/sentinel`)
- **Python** 3.11+ with a venv (camera clients)
- Webcam / video files for testing; on macOS grant Camera access to Terminal/Cursor

---

## Quick start

### 1. Database

Start MongoDB (example with Homebrew):

```bash
brew services start mongodb-community
```

### 2. API server

```bash
cd server
cp .env.example .env   # if you add one; or create .env as below
npm install
npm run build:ui       # builds frontend → server/static
npm run dev            # http://localhost:3000
```

**`server/.env`**

```env
MONGO_URI=mongodb://localhost:27017/sentinel
PORT=3000
JWT_SECRET=change-me-to-a-long-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=sentinel
CLIENT_ORIGIN=http://localhost:5173
```

| Variable | Purpose |
|----------|---------|
| `MONGO_URI` | MongoDB connection string |
| `PORT` | HTTP port (default `3000`) |
| `JWT_SECRET` | Signs admin cookies and camera tokens |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Dashboard login |
| `CLIENT_ORIGIN` | Allowed CORS origin for Vite hot-reload (`:5173`) |

Open the dashboard at **http://localhost:3000** and sign in with `admin` / `sentinel`.

### 3. Dashboard (optional hot reload)

```bash
# terminal A
cd server && npm run dev

# terminal B
cd frontend && npm install && npm run dev
# → http://localhost:5173 (proxies /api → :3000)
```

Production UI is always built with:

```bash
cd server && npm run build:ui
```

### 4. Camera clients (Python)

```bash
cd /path/to/sentinel
python -m venv .venv
source .venv/bin/activate

pip install -r cameras/facial-cam/requirements.txt
pip install -r cameras/surveillance-cam/requirements.txt
```

Cameras assume the API at **`http://localhost:3000`** (no URL prompt).

---

## Admin dashboard

Pages (after login):

| Page | What you do |
|------|-------------|
| **Overview** | Counts, recent motion, unread notifications |
| **Cameras** | Create facial/surveillance cams → copy one-time **access key**; revoke/delete |
| **Users** | Create person → copy one-time **enroll key**; Authorize / Revoke / Delete |
| **Motion alerts** | List human/animal/unknown alerts; **Clear all** |
| **Notifications** | Inbox (enroll, authorize, camera claim, motion); Mark read / **Clear all** |

Access keys and enroll keys are shown **once** at creation. Store them securely.

---

## Facial camera

```bash
cd cameras
python facial-cam/main.py claim    # pair device with dashboard access key
python facial-cam/main.py enroll   # enroll user with dashboard enroll key
python facial-cam/main.py run      # live recognition
```

### Commands

| Command | Prompts | Behavior |
|---------|---------|----------|
| `claim` | Camera access key (optional re-pair) | Saves JWT to `cameras/.tokens/facial.json` |
| `enroll` | Enroll key, image path or webcam | Crops closest face → uploads embedding + JPEG → user `enrolled` |
| `run` | Offline? / webcam or video path | Syncs gallery from API; holds **3s** continuous result then exits |

### Recognition rules

- Gallery includes users with status **`enrolled`** or **`authorized`** (must have face data).
- Match above similarity threshold **and** status `authorized` → **authorized**.
- Match but only `enrolled` → **unauthorized** (overlay: `name pending`).
- No match → **unauthorized**.
- Exit codes: `0` authorized, `2` unauthorized, `1` cancel/error.

Revoked cameras: saved tokens are checked via `GET /api/cameras/me`; invalid tokens are cleared and re-pairing is required.

**Offline mode** (`run` → offline yes): uses local folder `cameras/data/faces/authorized/<identity>/*.jpg` only (no API).

---

## Surveillance camera

```bash
cd cameras
python surveillance-cam/main.py claim
python surveillance-cam/main.py run
```

### `run` prompts

1. Offline (no dashboard alerts)?  
2. **Test with a local video file?** → path, or webcam index (default `0`)  
3. If online: upload snapshots?  

Pipeline per video loop:

1. Farneback optical flow → motion boxes  
2. Stability window (default ≥3 hits in 6 frames)  
3. DINOv3 ViT-S/16 + ImageNet probe → coarse class: `human` / `animal` / `unknown object`  
4. Labels shown on screen for the next window of frames  

### Alert aggregation (`motion_alerts.py`)

- At most **one** server notification every **10 seconds**.
- Over that window of detections:
  1. If **≥ 3%** are `human` → alert **human**
  2. Else if **≥ 5%** are `animal` → alert **animal**
  3. Else → **unknown object**

Each alert also creates a dashboard **notification**.

Token file: `cameras/.tokens/surveillance.json`.

---

## API reference (summary)

Base URL: `http://localhost:3000`

### Admin (cookie `token` after login)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | `{ username, password }` → sets httpOnly cookie |
| `POST` | `/api/auth/logout` | Clears cookie |
| `GET` | `/api/auth/me` | Current admin |
| `POST` | `/api/cameras` | `{ name, type: "facial"\|"surveillance", location? }` → `{ camera, accessKey }` |
| `GET` | `/api/cameras` | List cameras |
| `POST` | `/api/cameras/:id/revoke` | Status → `revoked` |
| `DELETE` | `/api/cameras/:id` | Delete camera |
| `POST` | `/api/users` | `{ username, email, fullName? }` → `{ user, enrollKey }` |
| `GET` | `/api/users` | List users |
| `POST` | `/api/users/:id/authorize` | `enrolled` → `authorized` + notification |
| `POST` | `/api/users/:id/revoke` | Revoke user |
| `DELETE` | `/api/users/:id` | Delete user |
| `GET` | `/api/alerts` | Motion alerts |
| `DELETE` | `/api/alerts` | Clear all alerts (+ motion notifications) |
| `GET` | `/api/notifications` | `?unread=1` optional |
| `POST` | `/api/notifications/read-all` | Mark all read |
| `DELETE` | `/api/notifications` | Clear all notifications |
| `POST` | `/api/notifications/:id/read` | Mark one read |

### Devices (Bearer camera JWT)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/cameras/claim` | `{ accessKey, deviceInfo? }` → `{ token, camera }` (no auth) |
| `GET` | `/api/cameras/me` | Validate token; fails if revoked |
| `POST` | `/api/enroll` | Facial: `{ enrollKey, faceImage?, embedding? }` |
| `GET` | `/api/enroll/gallery` | Facial: enrolled + authorized faces |
| `POST` | `/api/enroll/verify` | Facial: `{ username }` → access |
| `POST` | `/api/alerts` | Surveillance: `{ category, label?, confidence?, box?, snapshot? }` |

### Data models (MongoDB)

- **Camera** — `pending` → `active` (after claim) → `revoked`; type `facial` \| `surveillance`; access key stored as SHA-256 hash  
- **User** — `pending` → `enrolled` → `authorized` \| `revoked`; embedding + optional face JPEG (base64)  
- **Alert** — motion event linked to camera + category  
- **Notification** — dashboard inbox (`user_enrolled`, `user_authorized`, `camera_registered`, `motion_alert`, …)

---

## End-to-end checklist

1. Start MongoDB and `cd server && npm run build:ui && npm run dev`  
2. Login at http://localhost:3000 (`admin` / `sentinel`)  
3. **Cameras** → create *facial* + *surveillance* → copy access keys  
4. `python facial-cam/main.py claim` and `python surveillance-cam/main.py claim`  
5. **Users** → create user → copy enroll key  
6. `python facial-cam/main.py enroll` → SPACE to capture → Authorize on dashboard  
7. `python facial-cam/main.py run` → expect authorized after 3s hold  
8. `python surveillance-cam/main.py run` → optional local video → see alerts on dashboard  

---

## Scripts & extras

| Path | Notes |
|------|--------|
| `cameras/scripts/eval_moca_optical_flow.py` | MoCA dataset eval helper (needs MoCA data under `cameras/`) |
| `cameras/videos/` | Sample MP4s for surveillance local-video tests |
| `cameras/data/cascades/` | Viola–Jones Haar XML |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `MONGO_URI is missing` | Create `server/.env` (see above) |
| Dashboard 503 / blank | `cd server && npm run build:ui` |
| Camera denied on macOS | System Settings → Privacy → Camera → allow Terminal/Cursor |
| `Saved camera token rejected` | Camera was revoked; create a new camera key and `claim` again |
| Recognition always unauthorized / empty gallery | Authorize the user on the dashboard after enroll |
| CORS errors on `:5173` | Ensure `CLIENT_ORIGIN=http://localhost:5173` and server is running |
| Alerts flooding | Intended max is 1 alert / 10s via `MotionAlertAggregator` |

---

## Security notes

- Change `JWT_SECRET` and admin password before any real deployment.  
- Access keys and enroll keys are one-time; only hashes are stored.  
- Admin session uses httpOnly cookies; cameras use Bearer JWTs (30-day expiry on claim).  
- Do not commit `server/.env` or `cameras/.tokens/`.  

---

## License

ISC (see `server/package.json`).
