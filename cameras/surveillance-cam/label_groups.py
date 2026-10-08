"""Map ImageNet-1k labels → human / animal / unknown object.

ImageNet-1k convention used here:
  - class indices 0..397 are animals (tench … puffer)
  - a few later classes refer to people (groom, scuba diver)
  - everything else → unknown object
"""

from __future__ import annotations

# Inclusive end index of the contiguous animal block in ImageNet-1k.
IMAGENET_ANIMAL_INDEX_MAX = 397

# Explicit human-related ImageNet class names (outside the animal block).
HUMAN_LABELS: list[str] = [
    "groom",
    "scuba diver",
    "person",
    "man",
    "woman",
    "men",
    "women",
    "boy",
    "girl",
    "child",
    "baby",
    "human",
    "bridegroom",
    "ballplayer",
]

COARSE_CLASSES = ("human", "animal", "unknown object")


def coarse_category(label: str, class_idx: int | None = None) -> str:
    """Classify an ImageNet prediction into human / animal / unknown object."""
    if class_idx is not None and 0 <= class_idx <= IMAGENET_ANIMAL_INDEX_MAX:
        return "animal"

    low = label.lower().replace("_", " ").replace("-", " ")
    # Exact / substring match against human list (longer keys first).
    for key in sorted(HUMAN_LABELS, key=len, reverse=True):
        if key in low:
            return "human"

    return "unknown object"
