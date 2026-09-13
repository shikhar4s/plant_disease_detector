"""Lazy inference for the versioned PlantDoc classifier.

The evaluated EfficientNet checkpoint is preferred when present. The legacy
CNN remains as a compatibility fallback while an older deployment rolls out.
"""
import json
import threading
from functools import lru_cache

from django.conf import settings
from PIL import Image


def _artifact_path(name):
    return settings.BASE_DIR / "deployment_artifacts" / name


@lru_cache(maxsize=1)
def class_names():
    with _artifact_path("class_names.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def model_manifest():
    candidate = _artifact_path("model_manifest_efficientnet_b0.json")
    path = candidate if candidate.exists() else _artifact_path("model_manifest.json")
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest.setdefault("uncertainty_threshold", 0.80)
    return manifest


def display_name(label):
    return label.replace("___", " · ").replace("_", " ")


class ModelService:
    def __init__(self):
        self.model = None
        self.transform = None
        self.kind = None
        self.lock = threading.Lock()

    def _load(self):
        import torch

        torch.set_num_threads(1)
        efficient_weights = _artifact_path("plant_disease_model_efficientnet_b0.pth")
        if efficient_weights.exists():
            from torchvision import models

            weights = models.EfficientNet_B0_Weights.DEFAULT
            model = models.efficientnet_b0(weights=None)
            model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, len(class_names()))
            state = torch.load(efficient_weights, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            self.transform = weights.transforms()
            self.kind = "efficientnet-b0"
        else:
            import numpy as np
            from .model_architecture import CNN_NeuralNet

            model = CNN_NeuralNet(in_channels=3, num_diseases=len(class_names()))
            state = torch.load(_artifact_path("plant_disease_model.pth"), map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            self.transform = lambda picture: torch.from_numpy(
                np.asarray(picture.resize((256, 256), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
            ).permute(2, 0, 1).contiguous()
            self.kind = "legacy-cnn"
        model.eval()
        self.model = model

    def predict(self, image):
        import torch

        with self.lock:
            if self.model is None:
                self._load()
            tensor = self.transform(image.convert("RGB")).unsqueeze(0)
            with torch.inference_mode():
                scores, indices = torch.softmax(self.model(tensor), dim=1).topk(3, dim=1)
            predictions = [
                {"label": class_names()[index], "disease": display_name(class_names()[index]),
                 "confidence": round(score, 6)}
                for score, index in zip(scores[0].tolist(), indices[0].tolist())
            ]
            best = predictions[0]
            threshold = float(model_manifest().get("uncertainty_threshold", 0.80))
            status = ("uncertain" if best["confidence"] < threshold else
                      "healthy" if best["label"].lower().endswith("___healthy") else "possible_disease")
            return {"disease": best["label"], "confidence": best["confidence"], "status": status,
                    "model_version": model_manifest()["model_version"], "top_predictions": predictions}


model_service = ModelService()

