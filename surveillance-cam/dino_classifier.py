"""Smallest practical DINOv3 (ViT-S/16 via timm) + ImageNet-1k linear probe."""

from __future__ import annotations

import json
import sys
from functools import lru_cache

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from label_groups import COARSE_CLASSES, coarse_category

DEFAULT_TIMM_MODEL = "vit_small_patch16_dinov3.lvd1689m"
DEFAULT_PROBE = "canvit/dinov3-vits16-lvd1689m-in1k-512x512-linear-clf-probe"


def _imagenet_categories() -> list[str]:
    try:
        from torchvision.models import ResNet50_Weights

        return list(ResNet50_Weights.IMAGENET1K_V2.meta["categories"])
    except Exception:
        return [f"class_{i}" for i in range(1000)]


class Dinov3Classifier:
    """DINOv3 ViT-S/16 + ImageNet-1k probe → human / animal / unknown object."""

    def __init__(
        self,
        model_id: str = DEFAULT_TIMM_MODEL,
        probe_id: str = DEFAULT_PROBE,
        device: str | None = None,
    ) -> None:
        import timm
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file

        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        self.categories = _imagenet_categories()
        self.coarse_classes = COARSE_CLASSES

        print(f"Loading DINOv3 ViT-S/16 ({model_id}) on {device}…", file=sys.stderr)
        self.backbone = timm.create_model(model_id, pretrained=True, num_classes=0)
        self.backbone.to(device)
        self.backbone.eval()
        data_cfg = timm.data.resolve_model_data_config(self.backbone)
        self.transform = timm.data.create_transform(**data_cfg, is_training=False)

        print(f"Loading ImageNet linear probe {probe_id}…", file=sys.stderr)
        cfg_path = hf_hub_download(probe_id, "config.json")
        with open(cfg_path, encoding="utf-8") as fp:
            cfg = json.load(fp)
        in_features = int(cfg.get("in_features", 384))
        out_features = int(cfg.get("out_features", 1000))
        self.head = nn.Linear(in_features, out_features)
        weights_path = hf_hub_download(probe_id, "model.safetensors")
        state = load_file(weights_path)
        self.head.load_state_dict({"weight": state["weight"], "bias": state["bias"]})
        self.head.to(device)
        self.head.eval()

        with torch.inference_mode():
            dummy = torch.zeros(
                1, 3, data_cfg["input_size"][1], data_cfg["input_size"][2], device=device
            )
            feat = self.backbone(dummy)
            if feat.shape[-1] != in_features:
                raise RuntimeError(
                    f"DINOv3 feature dim {feat.shape[-1]} != probe in_features {in_features}"
                )

    @torch.inference_mode()
    def classify_bgr(self, crop_bgr: np.ndarray) -> tuple[str, str, float]:
        """Return (human|animal|unknown object, imagenet_label, confidence)."""
        if crop_bgr is None or crop_bgr.size == 0:
            return "unknown object", "unknown", 0.0
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        emb = self.backbone(tensor)
        if emb.ndim == 3:
            emb = emb[:, 0]
        logits = self.head(emb)
        probs = F.softmax(logits, dim=-1)[0]
        conf, idx = torch.max(probs, dim=-1)
        i = int(idx)
        label = self.categories[i] if i < len(self.categories) else str(i)
        short = label.split(",")[0].strip()
        return coarse_category(short, class_idx=i), short, float(conf)


@lru_cache(maxsize=1)
def get_classifier(model_id: str = DEFAULT_TIMM_MODEL) -> Dinov3Classifier:
    return Dinov3Classifier(model_id=model_id)
