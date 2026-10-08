#!/usr/bin/env python3
"""MoCA test: optical-flow stable borders + DINOv3 classification (with live display).

Builds MP4s from MoCA cat/dog/viper/rat sequences, runs the optical-flow pipeline
(stable ≥2/4 frames → classify → label next 4), shows each video on screen, and
writes annotated videos + events.jsonl.

Usage:
  python scripts/eval_moca_optical_flow.py
  python scripts/eval_moca_optical_flow.py --animals cat rat
  python scripts/eval_moca_optical_flow.py --no-display
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
MOCA = ROOT / "MoCA"
JPEG = MOCA / "JPEGImages"
OUT = ROOT / "output" / "moca_optical_flow"
OPTICAL = ROOT / "surveillance-cam"

ANIMAL_SEQUENCES: dict[str, list[str]] = {
    "cat": [
        "black_cat_0",
        "black_cat_1",
        "pallas_cat",
        "rusty_spotted_cat_0",
        "rusty_spotted_cat_1",
        "sand_cat_0",
    ],
    "dog": [
        "wolf",
        "arctic_wolf_0",
        "arctic_wolf_1",
    ],
    "viper": [
        "arabian_horn_viper",
        "copperhead_snake",
        "spider_tailed_horned_viper_0",
        "spider_tailed_horned_viper_1",
        "spider_tailed_horned_viper_2",
        "spider_tailed_horned_viper_3",
    ],
    "rat": [
        "rodent_x",
        "jerboa",
        "jerboa_1",
    ],
}

NOTES = {
    "cat": "MoCA cat sequences",
    "dog": "No dog in MoCA; wolf / arctic_wolf stand-in",
    "viper": "MoCA viper / copperhead_snake sequences",
    "rat": "No rat in MoCA; rodent_x / jerboa stand-in",
}


def select_frames(animal: str) -> list[Path]:
    selected: list[Path] = []
    for seq in ANIMAL_SEQUENCES[animal]:
        folder = JPEG / seq
        if folder.is_dir():
            selected.extend(sorted(folder.glob("*.jpg")))
    return selected


def frames_to_video(frames: list[Path], dest: Path, fps: int = 10) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    first = cv2.imread(str(frames[0]))
    if first is None:
        raise RuntimeError(f"Failed to read {frames[0]}")
    h, w = first.shape[:2]
    writer = cv2.VideoWriter(
        str(dest),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h),
    )
    for path in frames:
        img = cv2.imread(str(path))
        if img is None:
            continue
        if img.shape[0] != h or img.shape[1] != w:
            img = cv2.resize(img, (w, h))
        writer.write(img)
    writer.release()
    return dest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MoCA optical-flow + DINOv3 eval")
    p.add_argument(
        "--animals",
        nargs="+",
        default=["cat", "dog", "viper", "rat"],
        choices=list(ANIMAL_SEQUENCES),
    )
    p.add_argument("--no-display", action="store_true")
    p.add_argument("--magnitude", type=float, default=1.0)
    p.add_argument("--min-area", type=int, default=500)
    p.add_argument("--window", type=int, default=4)
    p.add_argument("--min-hits", type=int, default=2)
    p.add_argument("--device", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sys.path.insert(0, str(OPTICAL))
    from dino_classifier import Dinov3Classifier
    from main import run_video

    OUT.mkdir(parents=True, exist_ok=True)

    print("Loading DINOv3 once for all MoCA animals…", file=sys.stderr)
    classifier = Dinov3Classifier(device=args.device)

    summary: list[str] = []
    for animal in args.animals:
        frames = select_frames(animal)
        if not frames:
            print(f"[skip] {animal}: no frames", file=sys.stderr)
            continue

        animal_dir = OUT / animal
        animal_dir.mkdir(parents=True, exist_ok=True)
        video = frames_to_video(frames, animal_dir / f"{animal}_all.mp4")
        (animal_dir / "manifest.txt").write_text(
            "\n".join(
                [
                    f"animal={animal}",
                    f"note={NOTES[animal]}",
                    f"n_frames={len(frames)}",
                    f"sequences={','.join(ANIMAL_SEQUENCES[animal])}",
                    f"video={video}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        save_path = animal_dir / f"{animal}_optical_dino.mp4"
        events_path = animal_dir / "events.jsonl"
        print(
            f"[run] {animal}: {len(frames)} frames — press q to skip to next",
            file=sys.stderr,
        )
        events = run_video(
            str(video),
            save=str(save_path),
            events_path=str(events_path),
            display=not args.no_display,
            magnitude=args.magnitude,
            min_area=args.min_area,
            window=args.window,
            min_hits=args.min_hits,
            device=args.device,
            window_title=f"MoCA {animal} — optical flow + DINOv3 (q next)",
            classifier=classifier,
        )
        line = (
            f"{animal}: frames={len(frames)} "
            f"dino_events={len(events)} "
            f"video={save_path} events={events_path}"
        )
        summary.append(line)
        print(f"[done] {line}", file=sys.stderr)

    (OUT / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(
        json.dumps({"runs": summary}, indent=2) + "\n", encoding="utf-8"
    )
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
