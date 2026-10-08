# Sentinel dashboard (source)

React + Vite source. Production build is written to **`server/static`** and served by Express.

## Build into the server

```bash
cd frontend && npm run build
# or from server/
cd server && npm run build:ui
```

Then open the API host (same origin):

```bash
cd server && npm run dev
# → http://localhost:3000
```

## Dev (hot reload)

```bash
# terminal 1
cd server && npm run dev

# terminal 2 — Vite proxies /api → :3000
cd frontend && npm run dev
# → http://localhost:5173
```
