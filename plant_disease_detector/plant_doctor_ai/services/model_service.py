"""Lazy CPU inference using the project's original trained CNN."""
import json
import threading
from functools import lru_cache
from django.conf import settings
from PIL import Image


@lru_cache(maxsize=1)
def class_names():
    with open(settings.BASE_DIR / 'deployment_artifacts' / 'class_names.json', encoding='utf-8') as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def model_manifest():
    with open(settings.BASE_DIR / 'deployment_artifacts' / 'model_manifest.json', encoding='utf-8') as handle:
        return json.load(handle)


def display_name(label):
    return label.replace('___', ' · ').replace('_', ' ')


class ModelService:
    def __init__(self):
        self.model = None
        self.lock = threading.Lock()

    def predict(self, image):
        import numpy as np
        import torch
        from .model_architecture import CNN_NeuralNet

        with self.lock:
            if self.model is None:
                torch.set_num_threads(1)
                model = CNN_NeuralNet(in_channels=3, num_diseases=len(class_names()))
                weights = torch.load(settings.BASE_DIR / 'deployment_artifacts' / 'plant_disease_model.pth',
                                     map_location='cpu', weights_only=True)
                model.load_state_dict(weights)
                model.eval()
                self.model = model
            # Preserve training preprocessing: bilinear RGB resize and [0, 1].
            pixels = np.asarray(image.resize((256, 256), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
            tensor = torch.from_numpy(pixels).permute(2, 0, 1).unsqueeze(0).contiguous()
            with torch.inference_mode():
                scores, indices = torch.softmax(self.model(tensor), dim=1).topk(3, dim=1)
            predictions = [{'label': class_names()[index], 'disease': display_name(class_names()[index]),
                            'confidence': round(score, 6)}
                           for score, index in zip(scores[0].tolist(), indices[0].tolist())]
            best = predictions[0]
            threshold = float(model_manifest()['uncertainty_threshold'])
            status = ('uncertain' if best['confidence'] < threshold else
                      'healthy' if best['label'].lower().endswith('___healthy') else 'possible_disease')
            return {'disease': best['label'], 'confidence': best['confidence'], 'status': status,
                    'model_version': model_manifest()['model_version'], 'top_predictions': predictions}


model_service = ModelService()
