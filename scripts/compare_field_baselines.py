"""Evaluate old weights against the corrected field labels (regression only).

The old weights may have seen related images; these are not independent estimates
of old-model generalisation. Does not select or change production weights.
"""
import argparse
import json
import sys
from pathlib import Path

import torch
from torchvision import models, transforms
from torch.utils.data import DataLoader

from train_model_v2 import ImageListDataset
from train_field_candidate import metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo / 'plant_disease_detector'))
    from plant_doctor_ai.services.model_architecture import CNN_NeuralNet
    root = args.repo / 'plant_disease_detector/deployment_artifacts'
    classes = json.loads((root / 'class_names.json').read_text())
    data = json.loads((args.output / 'data_manifest.json').read_text())
    torch.set_num_threads(1)
    results = {}
    for name in ('legacy', 'staged-v1'):
        if name == 'legacy':
            model = CNN_NeuralNet(in_channels=3, num_diseases=len(classes))
            transform = transforms.Compose([transforms.Resize((256, 256)), transforms.ToTensor()])
            filename = 'plant_disease_model.pth'
        else:
            model = models.efficientnet_b0(weights=None)
            model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, len(classes))
            transform = models.EfficientNet_B0_Weights.DEFAULT.transforms()
            filename = 'plant_disease_model_efficientnet_b0.pth'
        model.load_state_dict(torch.load(root / filename, map_location='cpu', weights_only=True))
        model.eval()
        rows = data['partitions']['field_test']
        loader = DataLoader(ImageListDataset([(row['path'], row['label']) for row in rows], transform), batch_size=1)
        logits, labels = [], []
        with torch.inference_mode():
            for index, (images, target) in enumerate(loader):
                logits.append(model(images))
                labels.append(target)
                if (index + 1) % 50 == 0:
                    print(json.dumps({'model': name, 'completed': index + 1}), flush=True)
        results[name] = metrics(torch.cat(logits), torch.cat(labels), classes)
        print(json.dumps({'model': name, 'accuracy': results[name]['accuracy'], 'macro_f1': results[name]['macro_f1']}), flush=True)
    (args.output / 'baseline_comparison.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

