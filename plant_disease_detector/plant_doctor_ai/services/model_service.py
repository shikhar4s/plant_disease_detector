"""Lazy inference for the versioned PlantDoc classifier.

The selected artifact and manifest are explicit. Candidate files cannot silently
change the model or report a version that does not match the loaded weights.
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
    selection = json.loads(_artifact_path('selected_model.json').read_text(encoding='utf-8'))
    path = _artifact_path(selection['manifest'])
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
        self.temperature = 1.0
        self.centroids = None
        self.similarity_threshold = None
        self.lock = threading.Lock()

    def _load(self):
        import torch

        torch.set_num_threads(1)
        import hashlib
        selection = json.loads(_artifact_path('selected_model.json').read_text(encoding='utf-8'))
        selected_weights = _artifact_path(selection['filename'])
        with selected_weights.open('rb') as handle:
            if hashlib.file_digest(handle, 'sha256').hexdigest() != selection['sha256']:
                raise RuntimeError('Selected model checksum mismatch')
        if selection['filename'] in {'plant_disease_model_efficientnet_b0.pth', 'plant_disease_model_field_v2.pth'}:
            from torchvision import models

            weights = models.EfficientNet_B0_Weights.DEFAULT
            model = models.efficientnet_b0(weights=None)
            model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, len(class_names()))
            state = torch.load(selected_weights, map_location="cpu", weights_only=True)
            if selection['filename'] == 'plant_disease_model_field_v2.pth':
                if state['class_names'] != class_names():
                    raise RuntimeError('Checkpoint class mapping mismatch')
                self.temperature = float(state['temperature'])
                self.centroids = state['centroids']
                self.similarity_threshold = float(state['similarity_threshold'])
                state = state['state_dict']
            model.load_state_dict(state)
            self.transform = weights.transforms()
            self.kind = "efficientnet-b0"
        elif selection['filename'] == 'plant_disease_model.pth':
            import numpy as np
            from .model_architecture import CNN_NeuralNet

            model = CNN_NeuralNet(in_channels=3, num_diseases=len(class_names()))
            state = torch.load(selected_weights, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            self.transform = lambda picture: torch.from_numpy(
                np.asarray(picture.resize((256, 256), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
            ).permute(2, 0, 1).contiguous()
            self.kind = "legacy-cnn"
        else:
            raise RuntimeError('Unsupported selected architecture')
        model.eval()
        self.model = model

    def predict(self, image):
        import torch

        with self.lock:
            if self.model is None:
                self._load()
            tensor = self.transform(image.convert("RGB")).unsqueeze(0)
            with torch.inference_mode():
                similarity = None
                if self.centroids is not None:
                    features = self.model.avgpool(self.model.features(tensor)).flatten(1)
                    logits = self.model.classifier(features)
                else:
                    logits = self.model(tensor)
                scores, indices = torch.softmax(logits / self.temperature, dim=1).topk(3, dim=1)
                if self.centroids is not None:
                    similarity = float((torch.nn.functional.normalize(features, dim=1) * self.centroids[indices[0, 0]]).sum())
            predictions = [
                {"label": class_names()[index], "disease": display_name(class_names()[index]),
                 "confidence": round(score, 6)}
                for score, index in zip(scores[0].tolist(), indices[0].tolist())
            ]
            best = predictions[0]
            threshold = float(model_manifest().get("uncertainty_threshold", 0.80))
            rejected = best['confidence'] < threshold or (similarity is not None and similarity < self.similarity_threshold)
            status = ("uncertain" if rejected else
                      "healthy" if best["label"].lower().endswith("___healthy") else "possible_disease")
            return {"disease": best["label"], "confidence": best["confidence"], "status": status,
                    "model_version": model_manifest()["model_version"], "top_predictions": predictions}


model_service = ModelService()

