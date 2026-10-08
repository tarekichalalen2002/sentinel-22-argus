# Sentinel

Two camera pipelines:

1. **facial-cam** — Viola–Jones crop → InsightFace `buffalo_s` → authorized / unauthorized
2. **surveillance-cam** — optical flow → stable movers → DINOv3 → human / animal / unknown object

## Setup

```bash
cd sentinel
python -m venv .venv
source .venv/bin/activate

# Facial recognition
pip install -r facial-cam/requirements.txt

# Surveillance (optical flow + DINOv3)
pip install -r surveillance-cam/requirements.txt
```

## Facial cam

```bash
# Live recognition (exits after 3s continuous authorized/unauthorized)
python facial-cam/main.py run --source 0

# Enroll (asks admin username/password in the terminal)
python facial-cam/main.py enroll --user alice --source 0
python facial-cam/main.py enroll --user alice --image photo.jpg
```

Gallery layout: `data/faces/authorized/<user_id>/*.jpg`

On macOS, grant Camera access to Terminal/Cursor if webcam open fails.

## Surveillance cam

```bash
python surveillance-cam/main.py --source path/to/video.mp4
python surveillance-cam/main.py --source path/to/video.mp4 --save output/flow_dino.mp4
python surveillance-cam/main.py --source 0
```

### MoCA optical-flow eval

```bash
python scripts/eval_moca_optical_flow.py
python scripts/eval_moca_optical_flow.py --animals cat rat
```
