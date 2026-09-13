"""Evaluate the legacy PlantDoc model on the same mapped field-image holdout."""
import argparse
import json
import os
import sys
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "plant_disease_detector"))
from plant_doctor_ai.services.model_architecture import CNN_NeuralNet  # noqa: E402
from train_efficientnet import canonical_plantdoc, load_classes  # noqa: E402


class FieldImages(Dataset):
    def __init__(self, records):
        self.records = records
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
        ])

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        path, target = self.records[index]
        safe_path = ("\\\\?\\" + path) if os.name == "nt" and len(path) >= 240 and not path.startswith("\\\\?\\") else path
        with Image.open(safe_path) as image:
            image = image.convert("RGB")
        return self.transform(image), target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    repo_root = Path(args.repo_root)
    classes = load_classes(repo_root)
    class_to_index = {name: index for index, name in enumerate(classes)}
    records = []
    test_root = Path(args.data_root) / "PlantDoc-Dataset-master/test"
    for folder in test_root.iterdir():
        label = canonical_plantdoc(folder.name)
        if label not in class_to_index:
            continue
        for path in folder.glob("*"):
            if path.suffix.casefold() in {".jpg", ".jpeg", ".png"}:
                records.append((str(path), class_to_index[label]))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CNN_NeuralNet(in_channels=3, num_diseases=len(classes))
    weights = torch.load(repo_root / "plant_disease_detector/deployment_artifacts/plant_disease_model.pth", map_location="cpu", weights_only=True)
    model.load_state_dict(weights)
    model.to(device).eval()
    loader = DataLoader(FieldImages(records), batch_size=64, shuffle=False, num_workers=0)
    y_true, y_pred = [], []
    with torch.inference_mode():
        for images, targets in loader:
            pred = model(images.to(device)).argmax(1).cpu().tolist()
            y_true.extend(targets.tolist())
            y_pred.extend(pred)
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "count": len(y_true),
        "classification_report": classification_report(y_true, y_pred, labels=list(range(len(classes))), target_names=classes, output_dict=True, zero_division=0),
    }
    Path(args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({key: metrics[key] for key in ("accuracy", "precision_macro", "recall_macro", "macro_f1", "count")}, indent=2))


if __name__ == "__main__":
    main()

