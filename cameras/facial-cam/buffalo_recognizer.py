"""InsightFace buffalo_s recognition on Viola–Jones face crops."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class BuffaloRecognizer:
    """Embed faces with buffalo_s; match against an authorized gallery."""

    def __init__(
        self,
        gallery_dir: str | Path,
        *,
        model_name: str = "buffalo_s",
        threshold: float = 0.35,
        ctx_id: int = -1,
        det_size: tuple[int, int] = (320, 320),
    ) -> None:
        from insightface.app import FaceAnalysis

        self.gallery_dir = Path(gallery_dir)
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = float(threshold)
        self.model_name = model_name

        print(f"Loading InsightFace {model_name}…", file=sys.stderr)
        # Detection kept so we can refine landmarks inside a VJ crop when possible.
        self.app = FaceAnalysis(
            name=model_name,
            allowed_modules=["detection", "recognition"],
        )
        # ctx_id=-1 → CPU; 0 → first GPU
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)
        self.rec = self.app.models.get("recognition")
        if self.rec is None:
            raise RuntimeError(f"No recognition model in pack {model_name}")

        self.identities: dict[str, np.ndarray] = {}
        self._load_gallery()

    def _load_gallery(self) -> None:
        self.identities.clear()
        for user_dir in sorted(p for p in self.gallery_dir.iterdir() if p.is_dir()):
            embs: list[np.ndarray] = []
            for img_path in sorted(user_dir.iterdir()):
                if img_path.suffix.lower() not in _IMAGE_EXTS:
                    continue
                bgr = cv2.imread(str(img_path))
                if bgr is None:
                    continue
                emb = self.embed_bgr(bgr)
                if emb is not None:
                    embs.append(emb)
            if not embs:
                print(f"  skip empty/unreadable gallery user: {user_dir.name}", file=sys.stderr)
                continue
            mean = np.mean(np.stack(embs, axis=0), axis=0)
            mean = mean / (np.linalg.norm(mean) + 1e-8)
            self.identities[user_dir.name] = mean.astype(np.float32)
            print(
                f"  enrolled {user_dir.name}: {len(embs)} image(s)",
                file=sys.stderr,
            )
        print(
            f"Gallery ready: {len(self.identities)} identities from {self.gallery_dir}",
            file=sys.stderr,
        )

    def embed_bgr(self, crop_bgr: np.ndarray) -> np.ndarray | None:
        """Embedding for a Viola–Jones crop (BGR)."""
        if crop_bgr is None or crop_bgr.size == 0:
            return None

        # Prefer buffalo detection+align inside the crop for better landmarks.
        faces = self.app.get(crop_bgr)
        if faces:
            best = max(faces, key=lambda f: float(f.det_score))
            emb = getattr(best, "normed_embedding", None)
            if emb is not None:
                return np.asarray(emb, dtype=np.float32).ravel()

        # Fallback: resize crop to ArcFace 112×112 and run recognition head.
        aimg = cv2.resize(crop_bgr, (112, 112), interpolation=cv2.INTER_LINEAR)
        feat = self.rec.get_feat(aimg)
        emb = np.asarray(feat, dtype=np.float32).ravel()
        norm = float(np.linalg.norm(emb))
        if norm < 1e-8:
            return None
        return emb / norm

    def identify(
        self,
        crop_bgr: np.ndarray,
    ) -> tuple[str, str | None, float]:
        """Return (access, identity|None, similarity).

        access is authorized | unauthorized | no_face
        """
        emb = self.embed_bgr(crop_bgr)
        if emb is None:
            return "no_face", None, 0.0
        if not self.identities:
            return "unauthorized", None, 0.0

        best_name = None
        best_sim = -1.0
        for name, ref in self.identities.items():
            sim = float(np.dot(emb, ref))
            if sim > best_sim:
                best_sim = sim
                best_name = name

        if best_sim >= self.threshold:
            return "authorized", best_name, best_sim
        return "unauthorized", None, best_sim

    @property
    def enrolled_users(self) -> list[str]:
        return sorted(self.identities)
