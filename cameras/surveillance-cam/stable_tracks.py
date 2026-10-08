"""Associate motion boxes across frames and pick stable movers."""

from __future__ import annotations

from dataclasses import dataclass, field


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def box_center(b: tuple[int, int, int, int]) -> tuple[float, float]:
    x, y, w, h = b
    return x + w / 2.0, y + h / 2.0


@dataclass
class Track:
    track_id: int
    boxes: list[tuple[int, tuple[int, int, int, int]]] = field(default_factory=list)
    # frame_index within current window → box

    def add(self, frame_i: int, box: tuple[int, int, int, int]) -> None:
        self.boxes.append((frame_i, box))

    def appearances(self) -> int:
        return len({fi for fi, _ in self.boxes})

    def last_box(self) -> tuple[int, int, int, int]:
        return self.boxes[-1][1]

    def mean_box(self) -> tuple[int, int, int, int]:
        xs = [b[0] for _, b in self.boxes]
        ys = [b[1] for _, b in self.boxes]
        ws = [b[2] for _, b in self.boxes]
        hs = [b[3] for _, b in self.boxes]
        return (
            int(sum(xs) / len(xs)),
            int(sum(ys) / len(ys)),
            int(sum(ws) / len(ws)),
            int(sum(hs) / len(hs)),
        )


@dataclass
class LabeledRegion:
    box: tuple[int, int, int, int]
    category: str
    label: str
    confidence: float


class StabilityWindow:
    """Accumulate detections for `window` frames, keep tracks seen in >= min_hits."""

    def __init__(
        self,
        window: int = 4,
        min_hits: int = 2,
        match_iou: float = 0.3,
    ) -> None:
        self.window = window
        self.min_hits = min_hits
        self.match_iou = match_iou
        self.frame_i = 0
        self._tracks: list[Track] = []
        self._next_id = 1

    def reset(self) -> None:
        self.frame_i = 0
        self._tracks = []
        self._next_id = 1

    def update(self, boxes: list[tuple[int, int, int, int]]) -> None:
        """Add one frame of motion boxes (x, y, w, h)."""
        unmatched = set(range(len(boxes)))
        for track in self._tracks:
            best_j, best_iou = -1, 0.0
            for j in unmatched:
                score = iou(track.last_box(), boxes[j])
                if score > best_iou:
                    best_iou, best_j = score, j
            if best_j >= 0 and best_iou >= self.match_iou:
                track.add(self.frame_i, boxes[best_j])
                unmatched.remove(best_j)

        for j in unmatched:
            t = Track(track_id=self._next_id)
            self._next_id += 1
            t.add(self.frame_i, boxes[j])
            self._tracks.append(t)

        self.frame_i += 1

    def stable_tracks(self) -> list[Track]:
        return [t for t in self._tracks if t.appearances() >= self.min_hits]

    @property
    def full(self) -> bool:
        return self.frame_i >= self.window
