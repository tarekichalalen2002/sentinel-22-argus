"""Viola–Jones face crop + InsightFace buffalo_s ↔ Sentinel server.

Usage (keys / source are prompted interactively):
  python facial-cam/main.py claim
  python facial-cam/main.py enroll
  python facial-cam/main.py run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

DETECT_HOLD_SEC = 3.0
GALLERY_REFRESH_SEC = 30.0

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASCADE = ROOT / "data" / "cascades" / "haarcascade_frontalface_default.xml"
DEFAULT_GALLERY = ROOT / "data" / "faces" / "authorized"
DEFAULT_SERVER = "http://localhost:3000"

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
from buffalo_recognizer import BuffaloRecognizer  # noqa: E402
from common.prompts import ask, ask_enroll_key, ask_source, ask_yes_no  # noqa: E402
from common.server_client import (  # noqa: E402
    SentinelClient,
    SentinelClientError,
    bgr_to_jpeg_b64,
    jpeg_b64_to_bgr,
)


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


def make_client(server: str) -> SentinelClient:
    return SentinelClient(server, token_name="facial")


def register_camera(client: SentinelClient, *, claim_mode: bool = False) -> None:
    client.require_active(offer_reregister=claim_mode)


def sync_gallery(client: SentinelClient, recognizer: BuffaloRecognizer) -> int:
    users = client.gallery()
    return recognizer.set_identities_from_embeddings(
        users,
        decode_face=jpeg_b64_to_bgr,
    )


_ACCESS_COLOR = {
    "authorized": (40, 200, 40),
    "unauthorized": (40, 40, 255),
    "no_face": (0, 165, 255),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="facial-cam",
        description="Viola–Jones + buffalo_s facial camera linked to Sentinel server",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("claim", help="Register this device (prompts for access key)")
    sub.add_parser("run", help="Live recognition (prompts for source / keys)")
    sub.add_parser("enroll", help="Remote enroll (prompts for keys / source)")
    return p


def cmd_claim(_args: argparse.Namespace) -> int:
    client = make_client(DEFAULT_SERVER)
    try:
        register_camera(client, claim_mode=True)
    except SentinelClientError as exc:
        print(exc, file=sys.stderr)
        return 1
    cam = client.camera or {}
    print(f"Ready. Camera id={cam.get('id')} name={cam.get('name')} type={cam.get('type')}")
    return 0


def cmd_enroll(_args: argparse.Namespace) -> int:
    print(
        "Enroll a user created on the dashboard.\n"
        "You need their enroll key (Users → Create user).",
        file=sys.stderr,
    )
    client = make_client(DEFAULT_SERVER)
    try:
        register_camera(client, claim_mode=False)
    except SentinelClientError as exc:
        print(exc, file=sys.stderr)
        return 1

    enroll_key = ask_enroll_key()
    image_path = ask("Face image path (leave empty to use webcam)", default="")
    source = "0" if not image_path else None
    if not image_path:
        source = ask_source("0")

    try:
        cascade_path = resolve_cascade(DEFAULT_CASCADE)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        print("Failed to load Viola–Jones cascade", file=sys.stderr)
        return 1

    try:
        recognizer = BuffaloRecognizer(DEFAULT_GALLERY, model_name="buffalo_s", ctx_id=-1)
    except Exception as exc:
        print(f"Failed to load buffalo_s: {exc}", file=sys.stderr)
        return 1

    crop = None
    if image_path:
        bgr = cv2.imread(str(Path(image_path).expanduser()))
        if bgr is None:
            print(f"Could not read {image_path}", file=sys.stderr)
            return 1
        crop = crop_face(bgr, cascade) or bgr
    else:
        try:
            src = parse_source(source or "0")
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            print(f"Could not open camera {source}", file=sys.stderr)
            return 1
        print("Press SPACE to capture, q/ESC to cancel", file=sys.stderr)
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
            cv2.putText(
                preview,
                "SPACE = enroll to server",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.imshow("Enroll — SPACE snap", preview)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord(" "):
                crop = crop_face(frame, cascade)
                if crop is None:
                    print("No face in frame — try again", file=sys.stderr)
                    continue
                break
        cap.release()
        cv2.destroyAllWindows()

    if crop is None:
        print("No face captured", file=sys.stderr)
        return 1

    emb = recognizer.embed_bgr(crop)
    if emb is None:
        print("Could not compute face embedding", file=sys.stderr)
        return 1

    try:
        result = client.enroll(
            enroll_key,
            face_image_b64=bgr_to_jpeg_b64(crop),
            embedding=emb.astype(float).tolist(),
        )
    except SentinelClientError as exc:
        print(f"Enrollment failed: {exc}", file=sys.stderr)
        return 1

    user = result.get("user") or {}
    print(
        f"Enrolled {user.get('username')} — status={user.get('status')} "
        "(awaiting admin authorization on dashboard)"
    )
    return 0


def cmd_run(_args: argparse.Namespace) -> int:
    offline = ask_yes_no("Run offline (local gallery only)?", default=False)
    client: SentinelClient | None = None
    if not offline:
        client = make_client(DEFAULT_SERVER)
        try:
            register_camera(client)
        except SentinelClientError as exc:
            print(exc, file=sys.stderr)
            return 1

    source_raw = ask_source("0")
    try:
        source = parse_source(source_raw)
        cascade_path = resolve_cascade(DEFAULT_CASCADE)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        print(f"Failed to load cascade: {cascade_path}", file=sys.stderr)
        return 1

    try:
        recognizer = BuffaloRecognizer(
            DEFAULT_GALLERY,
            model_name="buffalo_s",
            threshold=0.35,
            ctx_id=-1,
        )
    except Exception as exc:
        print(
            f"Failed to load buffalo_s: {exc}\n"
            "Install with: pip install insightface onnxruntime",
            file=sys.stderr,
        )
        return 1

    last_refresh = 0.0
    if client is not None:
        try:
            sync_gallery(client, recognizer)
            last_refresh = time.time()
        except SentinelClientError as exc:
            print(f"Gallery sync failed: {exc}", file=sys.stderr)
            return 1

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(
            f"Could not open source {source_raw}. "
            "On macOS grant Camera access to Terminal/Cursor.",
            file=sys.stderr,
        )
        return 1

    window = "Facial-cam — Sentinel (q/ESC quit)"
    hold_sec = DETECT_HOLD_SEC
    refresh_sec = GALLERY_REFRESH_SEC
    mode = "offline" if client is None else f"server={DEFAULT_SERVER}"
    print(
        f"Viola–Jones → buffalo_s | {mode} | users={recognizer.enrolled_users} "
        f"| hold={hold_sec:.1f}s",
        file=sys.stderr,
    )

    pending: tuple[str, str | None, float, float] | None = None
    verdict: tuple[str, str | None, float] | None = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if (
            client is not None
            and refresh_sec > 0
            and time.time() - last_refresh >= refresh_sec
        ):
            try:
                sync_gallery(client, recognizer)
                last_refresh = time.time()
            except SentinelClientError as exc:
                print(f"Gallery refresh failed: {exc}", file=sys.stderr)

        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        ih, iw = gray.shape[:2]
        face = closest_face(gray, cascade)

        if face is not None:
            x, y, w, h = expand_rect(
                int(face[0]), int(face[1]), int(face[2]), int(face[3]), iw, ih
            )
            crop = frame[y : y + h, x : x + w]
            access, identity, score = recognizer.identify(crop)

            # Confirm still authorized on server when we have a local match.
            if client is not None and access == "authorized" and identity:
                try:
                    check = client.verify(identity)
                    if check.get("access") != "authorized":
                        access, identity = "unauthorized", None
                except SentinelClientError:
                    pass

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
            elif access == "unauthorized" and identity:
                text = f"{identity} pending ({score:.2f})"
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

        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            verdict = None
            break
        if verdict is not None:
            break

    cap.release()
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
    if args.command == "claim":
        return cmd_claim(args)
    if args.command == "enroll":
        return cmd_enroll(args)
    if args.command == "run":
        return cmd_run(args)
    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
