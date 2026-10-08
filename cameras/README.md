# Sentinel cameras

Python camera clients for the Sentinel server.

1. **facial-cam** — Viola–Jones + `buffalo_s` → enroll / authorize against the API  
2. **surveillance-cam** — optical flow + DINOv3 → motion alerts to the dashboard  

Keys, server URL, and camera source are entered interactively (not as CLI flags).

## Setup

```bash
source .venv/bin/activate
pip install -r cameras/facial-cam/requirements.txt
pip install -r cameras/surveillance-cam/requirements.txt
```

Start the API first (`cd server && npm run dev`).

## Pair a camera

1. In the dashboard, create a **facial** or **surveillance** camera and copy the access key.  
2. On the device:

```bash
cd cameras
python facial-cam/main.py claim
python surveillance-cam/main.py claim
```

You will be prompted for the server URL and access key. Tokens are saved under `cameras/.tokens/`.

## Facial cam

```bash
python facial-cam/main.py enroll   # prompts: server, access key (if needed), enroll key, source
python facial-cam/main.py run      # prompts: offline?, server, source
```

## Surveillance cam

```bash
python surveillance-cam/main.py run   # prompts: offline?, source, server, access key (if needed)
```
