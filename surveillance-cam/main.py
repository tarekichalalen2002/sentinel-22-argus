"""Optical-flow movers → stable borders (2/4 frames) → DINOv3 classify → label next 4.

Usage:
  python surveillance-cam/main.py --source path/to/video.mp4
  python surveillance-cam/main.py --source path/to/video.mp4 --save output/flow_dino.mp4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

from dino_classifier import Dinov3Classifier
from stable_tracks import StabilityWindow, LabeledRegion, iou

WINDOW = 6
MIN_HITS = 3


def parse_source(source: str) -> str | int:
    if source.isdigit():
        return int(source)
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    return str(path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Optical-flow + stable borders + DINOv3 classification"
    )
    p.add_argument("--source", required=True, help="MP4 path or webcam index")
    p.add_argument("--magnitude", type=float, default=1.0)
    p.add_argument("--min-area", type=int, default=500)
    p.add_argument("--window", type=int, default=WINDOW)
    p.add_argument("--min-hits", type=int, default=MIN_HITS)
    p.add_argument(
        "--dino-model",
        default="vit_small_patch16_dinov3.lvd1689m",
        help="Smallest usable DINOv3 (ViT-S/16 via timm)",
    )
    p.add_argument("--save", default=None)
    p.add_argument("--device", default=None)
    return p


def motion_boxes(
    prev_gray: np.ndarray,
    gray: np.ndarray,
    *,
    magnitude: float,
    min_area: int,
) -> tuple[list[tuple[int, int, int, int]], list]:
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray,
        gray,
        None,
        0.5,
        3,
        15,
        3,
        5,
        1.2,
        0,
    )
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    mask = (mag > magnitude).astype(np.uint8) * 255
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[tuple[int, int, int, int]] = []
    kept: list = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < min_area:
            continue
        boxes.append((x, y, w, h))
        kept.append(contour)
    return boxes, kept


def draw_borders(
    frame: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    contours: list,
    color: tuple[int, int, int] = (0, 255, 0),
) -> None:
    for contour in contours:
        cv2.drawContours(frame, [contour], -1, color, 2)
    for x, y, w, h in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)


def draw_labels(frame: np.ndarray, regions: list[LabeledRegion]) -> None:
    for reg in regions:
        x, y, w, h = reg.box
        color = {
            "human": (255, 180, 0),
            "animal": (0, 220, 0),
            "unknown object": (0, 165, 255),
        }.get(reg.category, (0, 255, 0))
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        text = f"{reg.category}: {reg.label} ({reg.confidence:.2f})"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        ty = max(th + 4, y - 8)
        cv2.rectangle(frame, (x, ty - th - 4), (x + tw + 6, ty + 2), color, -1)
        cv2.putText(
            frame,
            text,
            (x + 3, ty),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )


def match_labels_to_boxes(
    labels: list[LabeledRegion],
    boxes: list[tuple[int, int, int, int]],
    match_iou: float = 0.2,
) -> list[LabeledRegion]:
    """Re-anchor classification labels onto current motion boxes when possible."""
    if not labels:
        return []
    used = set()
    out: list[LabeledRegion] = []
    for lab in labels:
        best_j, best = -1, 0.0
        for j, box in enumerate(boxes):
            if j in used:
                continue
            score = iou(lab.box, box)
            if score > best:
                best, best_j = score, j
        if best_j >= 0 and best >= match_iou:
            used.add(best_j)
            out.append(
                LabeledRegion(
                    box=boxes[best_j],
                    category=lab.category,
                    label=lab.label,
                    confidence=lab.confidence,
                )
            )
        else:
            # Keep last known box if no current motion match
            out.append(lab)
    return out


def classify_stable(
    frame: np.ndarray,
    window: StabilityWindow,
    classifier: Dinov3Classifier,
) -> list[LabeledRegion]:
    labeled: list[LabeledRegion] = []
    h, w = frame.shape[:2]
    for track in window.stable_tracks():
        x, y, bw, bh = track.mean_box()
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w, x + bw), min(h, y + bh)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = frame[y1:y2, x1:x2]
        category, label, conf = classifier.classify_bgr(crop)
        labeled.append(
            LabeledRegion(
                box=(x1, y1, x2 - x1, y2 - y1),
                category=category,
                label=label,
                confidence=conf,
            )
        )
        print(
            f"DINOv3 stable track#{track.track_id}: {category}/{label} ({conf:.2f})",
            file=sys.stderr,
        )
    return labeled


def run_video(
    source: str | int,
    *,
    save: str | Path | None = None,
    events_path: str | Path | None = None,
    display: bool = True,
    magnitude: float = 1.0,
    min_area: int = 500,
    window: int = WINDOW,
    min_hits: int = MIN_HITS,
    dino_model: str = "vit_small_patch16_dinov3.lvd1689m",
    device: str | None = None,
    window_title: str = "Optical flow + DINOv3 (q/ESC quit)",
    classifier: Dinov3Classifier | None = None,
) -> list[dict]:
    """Run optical-flow → stable borders → DINOv3 on one video. Returns event dicts."""
    import json
    import time

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    ret, prev_frame = cap.read()
    if not ret:
        raise RuntimeError("Could not read first frame")

    if classifier is None:
        classifier = Dinov3Classifier(model_id=dino_model, device=device)
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    writer = None
    events: list[dict] = []
    events_fp = None
    if events_path is not None:
        events_path = Path(events_path)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_fp = events_path.open("w", encoding="utf-8")

    collect = StabilityWindow(window=window, min_hits=min_hits)
    phase = "collect"
    display_left = 0
    active_labels: list[LabeledRegion] = []
    frame_idx = 0

    print(
        f"Optical flow on {source} | "
        f"stable ≥{min_hits}/{window} → DINOv3 → label next {window}",
        file=sys.stderr,
    )

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            boxes, contours = motion_boxes(
                prev_gray,
                gray,
                magnitude=magnitude,
                min_area=min_area,
            )

            if phase == "collect":
                collect.update(boxes)
                draw_borders(frame, boxes, contours, color=(0, 255, 0))
                cv2.putText(
                    frame,
                    f"collecting {collect.frame_i}/{window}",
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                if collect.full:
                    active_labels = classify_stable(frame, collect, classifier)
                    for lab in active_labels:
                        event = {
                            "ts": time.time(),
                            "frame": frame_idx,
                            "category": lab.category,
                            "label": lab.label,
                            "confidence": round(lab.confidence, 4),
                            "bbox": list(lab.box),
                        }
                        events.append(event)
                        if events_fp is not None:
                            events_fp.write(json.dumps(event) + "\n")
                            events_fp.flush()
                    collect.reset()
                    phase = "display"
                    display_left = window
            else:
                active_labels = match_labels_to_boxes(active_labels, boxes)
                draw_borders(frame, boxes, contours, color=(80, 80, 80))
                draw_labels(frame, active_labels)
                cv2.putText(
                    frame,
                    f"DINOv3 labels {window - display_left + 1}/{window}",
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                display_left -= 1
                if display_left <= 0:
                    active_labels = []
                    phase = "collect"

            if save:
                if writer is None:
                    fh, fw = frame.shape[:2]
                    Path(save).expanduser().parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(
                        str(Path(save).expanduser()),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        float(fps),
                        (fw, fh),
                    )
                writer.write(frame)

            if display:
                cv2.imshow(window_title, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break

            prev_gray = gray
    finally:
        cap.release()
        if writer is not None:
            writer.release()
            print(f"Saved {save}", file=sys.stderr)
        if events_fp is not None:
            events_fp.close()
        if display:
            cv2.destroyAllWindows()

    return events


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = parse_source(args.source)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    run_video(
        source,
        save=args.save,
        display=True,
        magnitude=args.magnitude,
        min_area=args.min_area,
        window=args.window,
        min_hits=args.min_hits,
        dino_model=args.dino_model,
        device=args.device,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
