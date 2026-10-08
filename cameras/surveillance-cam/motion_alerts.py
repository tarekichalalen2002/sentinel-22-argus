"""Aggregate moving-object classifications before notifying the server."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class DetectionSample:
    category: str
    label: str
    confidence: float
    box: tuple[int, int, int, int] | None = None
    snapshot_b64: str | None = None


class MotionAlertAggregator:
    """Buffer mover classes and emit at most one server alert every `window_sec`.

    Decision bias over the window (checked in order):
      1. if human detections are ≥ `human_ratio`  → "human"   (default 3%)
      2. elif animal detections are ≥ `animal_ratio` → "animal" (default 5%)
      3. otherwise → "unknown object"
    """

    def __init__(
        self,
        send: Callable[[dict[str, Any]], None],
        *,
        window_sec: float = 10.0,
        human_ratio: float = 0.03,
        animal_ratio: float = 0.05,
    ) -> None:
        self._send = send
        self.window_sec = float(window_sec)
        self.human_ratio = float(human_ratio)
        self.animal_ratio = float(animal_ratio)
        self._window_start: float | None = None
        self._samples: list[DetectionSample] = []

    def add(
        self,
        *,
        category: str,
        label: str = "",
        confidence: float = 0.0,
        box: tuple[int, int, int, int] | None = None,
        snapshot_b64: str | None = None,
    ) -> None:
        now = time.time()
        if self._window_start is None:
            self._window_start = now

        self._samples.append(
            DetectionSample(
                category=category,
                label=label or "",
                confidence=float(confidence),
                box=box,
                snapshot_b64=snapshot_b64,
            )
        )

        if now - self._window_start >= self.window_sec:
            self.flush()

    def flush(self) -> None:
        """Send one aggregated alert for the current window (if any samples)."""
        if not self._samples:
            self._window_start = None
            return

        total = len(self._samples)
        human_n = sum(1 for s in self._samples if s.category == "human")
        animal_n = sum(1 for s in self._samples if s.category == "animal")
        human_share = human_n / total
        animal_share = animal_n / total

        if human_share >= self.human_ratio:
            category = "human"
            pool = [s for s in self._samples if s.category == "human"]
        elif animal_share >= self.animal_ratio:
            category = "animal"
            pool = [s for s in self._samples if s.category == "animal"]
        else:
            category = "unknown object"
            pool = list(self._samples)

        best = max(pool, key=lambda s: s.confidence)
        payload: dict[str, Any] = {
            "category": category,
            "label": best.label,
            "confidence": best.confidence,
            "box": best.box,
            "snapshot_b64": best.snapshot_b64,
            "window_samples": total,
            "human_share": round(human_share, 4),
            "animal_share": round(animal_share, 4),
        }
        self._send(payload)
        self._samples = []
        self._window_start = None
