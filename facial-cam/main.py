"""Viola–Jones face crop + InsightFace buffalo_s recognition (webcam / video).

Pipeline:
  camera → Viola–Jones detect → padded face crop → buffalo_s embedding
        → match gallery → authorized / unauthorized

Usage:
  python facial-cam/main.py run --source 0
  python facial-cam/main.py enroll --user alice --image photo.jpg
  python facial-cam/main.py enroll --user alice --source 0
  # enroll asks admin username/password in the terminal (default admin / sentinel)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

DETECT_HOLD_SEC = 3.0

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASCADE = ROOT / "data" / "cascades" / "haarcascade_frontalface_default.xml"
DEFAULT_GALLERY = ROOT / "data" / "faces" / "authorized"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import require_admin  # noqa: E402
from buffalo_recognizer import BuffaloRecognizer  # noqa: E402


def resolve_cascade(path: str | Path | None = None) -> Path:
    if path is not None:
        p = Path(path).expanduser()
        if p.is_file():
            return p
    if DEFAULT_CASCADE.is_file():
        return DEFAULT_CASCADE
    opencv = Path(getattr(cv2.data, "haarcascades", "")) / (
        "haarcascade_frontalface_default.xml"
    )
    if opencv.is_file():
        return opencv
    raise FileNotFoundError(
        f"Viola–Jones cascade not found. Expected {DEFAULT_CASCADE}"
    )


def parse_source(source: str) -> str | int:
    if source.isdigit():
        return int(source)
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    return str(path)


def expand_rect(
    x: int,
    y: int,
    w: int,
    h: int,
    img_w: int,
    img_h: int,
    *,
    pad_x: float = 0.20,
    pad_top: float = 0.35,
    pad_bottom: float = 0.25,
) -> tuple[int, int, int, int]:
    left = int(w * pad_x)
    right = int(w * pad_x)
    top = int(h * pad_top)
    bottom = int(h * pad_bottom)
    x0 = max(0, x - left)
    y0 = max(0, y - top)
    x1 = min(img_w, x + w + right)
    y1 = min(img_h, y + h + bottom)
    return x0, y0, x1 - x0, y1 - y0


def face_contour(x: int, y: int, w: int, h: int, n: int = 36) -> np.ndarray:
    cx, cy = x + w / 2.0, y + h / 2.0
    rx, ry = w / 2.0, h / 2.0
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.stack(
        [cx + rx * np.cos(angles), cy + ry * np.sin(angles)],
        axis=1,
    )
    return pts.astype(np.int32).reshape(-1, 1, 2)


def closest_face(
    gray,
    cascade,
    *,
    scale_factor: float = 1.1,
    min_neighbors: int = 5,
    min_size: int = 60,
):
    """Return the closest Viola–Jones face (largest box ≈ nearer to camera)."""
    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        minSize=(min_size, min_size),
    )
    if len(faces) == 0:
        return None
    return max(faces, key=lambda r: int(r[2]) * int(r[3]))


def crop_face(bgr, cascade, **detect_kw):
    gray = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    ih, iw = gray.shape[:2]
    face = closest_face(gray, cascade, **detect_kw)
    if face is None:
        return None
    x, y, w, h = map(int, face)
    x, y, w, h = expand_rect(x, y, w, h, iw, ih)
    return bgr[y : y + h, x : x + w].copy()


_ACCESS_COLOR = {
    "authorized": (40, 200, 40),
    "unauthorized": (40, 40, 255),
    "no_face": (0, 165, 255),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="facial-cam",
        description="Viola–Jones crop + buffalo_s face recognition",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ---- run ----
    run_p = sub.add_parser("run", help="Live recognition from cam / video")
    run_p.add_argument("--source", default="0", help="Webcam index or video path")
    run_p.add_argument("--cascade", default=str(DEFAULT_CASCADE))
    run_p.add_argument("--gallery", default=str(DEFAULT_GALLERY))
    run_p.add_argument("--model", default="buffalo_s", help="InsightFace model pack")
    run_p.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Cosine similarity threshold for authorized match",
    )
    run_p.add_argument("--scale-factor", type=float, default=1.1)
    run_p.add_argument("--min-neighbors", type=int, default=5)
    run_p.add_argument("--min-size", type=int, default=60)
    run_p.add_argument(
        "--ctx-id",
        type=int,
        default=-1,
        help="InsightFace device: -1=CPU, 0=GPU0",
    )
    run_p.add_argument("--save", default=None, help="Optional output MP4")
    run_p.add_argument(
        "--hold-sec",
        type=float,
        default=DETECT_HOLD_SEC,
        help="Seconds of continuous authorized/unauthorized detection before exit",
    )

    # ---- enroll ----
    en_p = sub.add_parser(
        "enroll",
        help="Enroll an authorized face (Viola–Jones crop → gallery)",
    )
    en_p.add_argument("--user", required=True, help="Identity name (gallery folder)")
    en_p.add_argument("--image", default=None, help="Path to a face photo")
    en_p.add_argument(
        "--source",
        default=None,
        help="Webcam index to capture (SPACE to snap), e.g. 0",
    )
    en_p.add_argument("--gallery", default=str(DEFAULT_GALLERY))
    en_p.add_argument("--cascade", default=str(DEFAULT_CASCADE))
    en_p.add_argument(
        "--credentials",
        default=str(Path(__file__).resolve().parent / "credentials.yaml"),
        help="Path to admin credentials YAML",
    )

    return p


def cmd_enroll(args: argparse.Namespace) -> int:
    # Gate enrollment behind interactive admin username/password (terminal only).
    require_admin(credentials_path=args.credentials)

    try:
        cascade_path = resolve_cascade(args.cascade)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        print("Failed to load Viola–Jones cascade", file=sys.stderr)
        return 1

    user_dir = Path(args.gallery).expanduser() / args.user
    user_dir.mkdir(parents=True, exist_ok=True)

    if args.image:
        img_path = Path(args.image).expanduser()
        bgr = cv2.imread(str(img_path))
        if bgr is None:
            print(f"Could not read {args.image}", file=sys.stderr)
            return 1
        crop = crop_face(bgr, cascade)
        if crop is None:
            print("No face found — saving full image", file=sys.stderr)
            crop = bgr
        dest = user_dir / img_path.name
        cv2.imwrite(str(dest), crop)
        print(f"Enrolled {args.user} → {dest}")
        print("Enrollment successful. Exiting.")
        return 0

    if args.source is not None:
        src = int(args.source) if str(args.source).isdigit() else args.source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"Could not open camera {args.source}", file=sys.stderr)
            return 1
        print("Press SPACE to capture once, q/ESC to cancel", file=sys.stderr)
        n = len(list(user_dir.glob("*")))
        enrolled = False
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            preview = frame.copy()
            gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            face = closest_face(gray, cascade)
            if face is not None:
                x, y, w, h = map(int, face)
                ih, iw = gray.shape[:2]
                x, y, w, h = expand_rect(x, y, w, h, iw, ih)
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("Enroll — SPACE snap", preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord(" "):
                crop = crop_face(frame, cascade)
                if crop is None:
                    print("No face in frame — try again", file=sys.stderr)
                    continue
                n += 1
                dest = user_dir / f"capture_{n:03d}.jpg"
                cv2.imwrite(str(dest), crop)
                print(f"Enrolled {args.user} → {dest}")
                print("Enrollment successful. Exiting.")
                enrolled = True
                break
        cap.release()
        cv2.destroyAllWindows()
        return 0 if enrolled else 1

    print("enroll requires --image or --source", file=sys.stderr)
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    try:
        source = parse_source(args.source)
        cascade_path = resolve_cascade(args.cascade)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        print(f"Failed to load cascade: {cascade_path}", file=sys.stderr)
        return 1

    try:
        recognizer = BuffaloRecognizer(
            args.gallery,
            model_name=args.model,
            threshold=args.threshold,
            ctx_id=args.ctx_id,
        )
    except Exception as exc:
        print(
            f"Failed to load {args.model}: {exc}\n"
            "Install with: pip install insightface onnxruntime",
            file=sys.stderr,
        )
        return 1

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(
            f"Could not open source {args.source}. "
            "On macOS grant Camera access to Terminal/Cursor.",
            file=sys.stderr,
        )
        return 1

    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    writer = None
    window = "Facial-cam — VJ + buffalo_s (q/ESC quit)"
    hold_sec = float(args.hold_sec)
    print(
        f"Viola–Jones crop → {args.model} | gallery={args.gallery} "
        f"| users={recognizer.enrolled_users} | hold={hold_sec:.1f}s",
        file=sys.stderr,
    )

    # (access, identity, score, started_at)
    pending: tuple[str, str | None, float, float] | None = None
    verdict: tuple[str, str | None, float] | None = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        ih, iw = gray.shape[:2]
        # Crop / recognize only the closest face (largest Viola–Jones box).
        face = closest_face(
            gray,
            cascade,
            scale_factor=args.scale_factor,
            min_neighbors=args.min_neighbors,
            min_size=args.min_size,
        )

        if face is not None:
            x, y, w, h = expand_rect(
                int(face[0]), int(face[1]), int(face[2]), int(face[3]), iw, ih
            )
            crop = frame[y : y + h, x : x + w]
            access, identity, score = recognizer.identify(crop)

            if access in ("authorized", "unauthorized"):
                now = time.time()
                if (
                    pending is not None
                    and pending[0] == access
                    and pending[1] == identity
                ):
                    held = now - pending[3]
                else:
                    pending = (access, identity, score, now)
                    held = 0.0
                if held >= hold_sec:
                    verdict = (access, identity, score)
            else:
                pending = None

            color = _ACCESS_COLOR.get(access, (0, 255, 0))
            contour = face_contour(x, y, w, h)
            cv2.drawContours(frame, [contour], -1, color, 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 1)

            if access == "authorized" and identity:
                text = f"{identity} ({score:.2f})"
            elif access == "unauthorized":
                text = f"unauthorized ({score:.2f})"
            else:
                text = "no_face"

            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            ty = max(th + 4, y - 8)
            cv2.rectangle(frame, (x, ty - th - 4), (x + tw + 6, ty + 2), color, -1)
            cv2.putText(
                frame,
                text,
                (x + 3, ty),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        else:
            pending = None

        status = "waiting for face…"
        if pending is not None:
            rem = max(0.0, hold_sec - (time.time() - pending[3]))
            status = f"{pending[0]}… {rem:.1f}s"
        cv2.putText(
            frame,
            f"{'closest face' if face is not None else 'no face'} | {status}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
        )

        if args.save:
            if writer is None:
                fh, fw = frame.shape[:2]
                Path(args.save).expanduser().parent.mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(
                    str(Path(args.save).expanduser()),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    float(fps),
                    (fw, fh),
                )
            writer.write(frame)

        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            verdict = None
            break
        if verdict is not None:
            break

    cap.release()
    if writer is not None:
        writer.release()
        print(f"Saved {args.save}", file=sys.stderr)
    cv2.destroyAllWindows()

    if verdict is None:
        print("No verdict (cancelled or stream ended).", file=sys.stderr)
        return 1

    access, identity, score = verdict
    if access == "authorized":
        print(f"RESULT: authorized identity={identity} score={score:.3f}")
        return 0
    print(f"RESULT: unauthorized score={score:.3f}")
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "enroll":
        return cmd_enroll(args)
    if args.command == "run":
        return cmd_run(args)
    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
