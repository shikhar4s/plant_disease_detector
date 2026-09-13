"""Train and evaluate the PlantDoc EfficientNet-B0 candidate.

This script is intentionally separate from the production service. It uses the
official PlantVillage color split for validation/test and the held-out PlantDoc
test split as a field-image check. Exact-byte duplicate groups are kept in one
split; the manifest and metrics are written with the exported checkpoint.
"""
import argparse
import hashlib
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFile
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from torch import nn
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

ImageFile.LOAD_TRUNCATED_IMAGES = False
SEED = 20260913
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)


def load_classes(repo_root):
    return json.loads((repo_root / 'plant_disease_detector/deployment_artifacts/class_names.json').read_text(encoding='utf-8'))


def canonical_plantdoc(folder):
    value = folder.casefold().replace('_', ' ')
    crop = 'Bell pepper' if 'bell pepper' in value else 'Corn (maize)' if 'corn' in value else 'Grape' if 'grape' in value else 'Soybean' if 'soyabean' in value else None
    if 'apple' in value: crop = 'Apple'
    elif 'blueberry' in value: crop = 'Blueberry'
    elif 'cherry' in value: crop = 'Cherry (including sour)'
    elif 'peach' in value: crop = 'Peach'
    elif 'potato' in value: crop = 'Potato'
    elif 'raspberry' in value: crop = 'Raspberry'
    elif 'squash' in value: crop = 'Squash'
    elif 'strawberry' in value: crop = 'Strawberry'
    elif 'tomato' in value: crop = 'Tomato'
    if not crop: return None
    if 'scab' in value: disease = 'Apple_scab'
    elif 'black rot' in value: disease = 'Black_rot' if crop == 'Apple' else 'Black_rot'
    elif 'rust' in value: disease = 'Cedar_apple_rust' if crop == 'Apple' else 'Common_rust_'
    elif 'powdery mildew' in value: disease = 'Powdery_mildew'
    elif 'gray leaf spot' in value or 'cercospora' in value: disease = 'Cercospora_leaf_spot Gray_leaf_spot'
    elif 'corn leaf blight' in value: disease = 'Northern_Leaf_Blight'
    elif 'early blight' in value: disease = 'Early_blight'
    elif 'late blight' in value: disease = 'Late_blight'
    elif 'bacterial spot' in value: disease = 'Bacterial_spot'
    elif 'mosaic virus' in value: disease = 'Tomato_mosaic_virus'
    elif 'yellow virus' in value: disease = 'Tomato_Yellow_Leaf_Curl_Virus'
    elif 'mold' in value: disease = 'Leaf_Mold'
    elif 'septoria' in value: disease = 'Septoria_leaf_spot'
    elif 'two spotted' in value: disease = 'Spider_mites Two-spotted_spider_mite'
    elif 'leaf black rot' in value: disease = 'Black_rot'
    elif crop == 'Bell pepper' and 'spot' in value: disease = 'Bacterial_spot'
    else: disease = 'healthy'
    label = f'{crop}___{disease}'
    return label


class Samples(Dataset):
    def __init__(self, records, transform): self.records, self.transform = records, transform
    def __len__(self): return len(self.records)
    def __getitem__(self, index):
        path, target = self.records[index]
        safe_path = ('\\\\?\\' + path) if os.name == 'nt' and len(path) >= 240 and not path.startswith('\\\\?\\') else path
        with Image.open(safe_path) as image: image = image.convert('RGB')
        return self.transform(image), target


def files_by_label(root, classes):
    records = []
    for label in classes:
        folder = root / label
        for path in sorted(folder.glob('*')):
            if path.suffix.casefold() in {'.jpg', '.jpeg', '.png'}:
                records.append((str(path), classes.index(label)))
    return records


def group_split(records, val_size, test_size):
    groups = defaultdict(list)
    for path, label in records:
        groups[(hashlib.sha256(Path(path).read_bytes()).hexdigest(), label)].append((path, label))
    keys = list(groups)
    labels = [key[1] for key in keys]
    train_keys, rest_keys = train_test_split(keys, test_size=val_size + test_size, stratify=labels, random_state=SEED)
    rest_labels = [key[1] for key in rest_keys]
    ratio = test_size / (val_size + test_size)
    val_keys, test_keys = train_test_split(rest_keys, test_size=ratio, stratify=rest_labels, random_state=SEED)
    return [item for key in train_keys for item in groups[key]], [item for key in val_keys for item in groups[key]], [item for key in test_keys for item in groups[key]]


def cap_per_class(records, maximum):
    grouped = defaultdict(list)
    for record in records: grouped[record[1]].append(record)
    return [item for label in sorted(grouped) for item in sorted(grouped[label])[:maximum]]


def evaluate(model, loader, device, classes, output_dir, name):
    model.eval(); y_true = []; y_pred = []; confidences = []
    with torch.inference_mode():
        for images, targets in loader:
            logits = model(images.to(device)); probabilities = torch.softmax(logits, 1)
            confidence, predictions = probabilities.max(1)
            y_true.extend(targets.tolist()); y_pred.extend(predictions.cpu().tolist()); confidences.extend(confidence.cpu().tolist())
    report = classification_report(y_true, y_pred, labels=list(range(len(classes))), target_names=classes, output_dict=True, zero_division=0)
    metrics = {'accuracy': accuracy_score(y_true, y_pred), 'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
               'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0), 'macro_f1': f1_score(y_true, y_pred, average='macro', zero_division=0),
               'count': len(y_true), 'classification_report': report, 'confusion_matrix': confusion_matrix(y_true, y_pred, labels=list(range(len(classes)))).tolist()}
    (output_dir / f'{name}_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    return metrics, np.asarray(confidences), np.asarray(y_true) == np.asarray(y_pred)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--repo-root', required=True); parser.add_argument('--data-root', required=True); parser.add_argument('--epochs', type=int, default=8); parser.add_argument('--output-dir', required=True)
    args = parser.parse_args(); repo_root = Path(args.repo_root); data_root = Path(args.data_root); output_dir = Path(args.output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    classes = load_classes(repo_root); class_to_index = {name: index for index, name in enumerate(classes)}
    pv_root = data_root / 'PlantVillage-Dataset-master/raw/color'; pv_records = files_by_label(pv_root, classes)
    split_file = output_dir / 'pv_split_manifest.json'
    if split_file.exists():
        split_data = json.loads(split_file.read_text(encoding='utf-8'))
        pv_train, pv_val, pv_test = [tuple(item) for item in split_data['train']], [tuple(item) for item in split_data['validation']], [tuple(item) for item in split_data['test']]
    else:
        pv_train, pv_val, pv_test = group_split(pv_records, .10, .10)
        split_file.write_text(json.dumps({'train': pv_train, 'validation': pv_val, 'test': pv_test}), encoding='utf-8')
    field_records = []
    for split in ('train', 'test'):
        for folder in (data_root / f'PlantDoc-Dataset-master/{split}').iterdir():
            label = canonical_plantdoc(folder.name)
            if label not in class_to_index: continue
            for path in folder.glob('*'):
                if path.suffix.casefold() in {'.jpg', '.jpeg', '.png'}: field_records.append((split, str(path), class_to_index[label]))
    field_train = [(path, label) for split, path, label in field_records if split == 'train']; field_test = [(path, label) for split, path, label in field_records if split == 'test']
    # Keep local training bounded while retaining the full leakage-controlled
    # validation/test sets and every available field-image training sample.
    train_records = cap_per_class(pv_train, 100) + field_train
    weights = models.EfficientNet_B0_Weights.DEFAULT
    train_transform = transforms.Compose([transforms.RandomResizedCrop(224, scale=(.65, 1.0)), transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(p=.15), transforms.ColorJitter(.2, .2, .2, .05), transforms.ToTensor(), transforms.Normalize(weights.transforms().mean, weights.transforms().std), transforms.RandomErasing(p=.15)])
    eval_transform = weights.transforms()
    loaders = {
        'train': DataLoader(Samples(train_records, train_transform), batch_size=64, shuffle=True, num_workers=0, pin_memory=True),
        'val': DataLoader(Samples(pv_val, eval_transform), batch_size=128, shuffle=False, num_workers=0, pin_memory=True),
        'test': DataLoader(Samples(pv_test, eval_transform), batch_size=128, shuffle=False, num_workers=0, pin_memory=True),
        'field': DataLoader(Samples(field_test, eval_transform), batch_size=128, shuffle=False, num_workers=0, pin_memory=True),
    }
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu'); model = models.efficientnet_b0(weights=weights); model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes)); model.to(device)
    for parameter in model.features.parameters(): parameter.requires_grad = False
    optimizer = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4); scaler = GradScaler(enabled=device.type == 'cuda'); best = float('inf'); best_state = None
    for epoch in range(args.epochs):
        if epoch == 2:
            for parameter in model.features[-4:].parameters(): parameter.requires_grad = True
            optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=2e-5, weight_decay=1e-4)
        model.train(); running = 0.0
        for images, targets in loaders['train']:
            optimizer.zero_grad(set_to_none=True)
            with autocast(enabled=device.type == 'cuda'):
                loss = nn.functional.cross_entropy(model(images.to(device)), targets.to(device), label_smoothing=.05)
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update(); running += loss.item() * len(targets)
        model.eval(); val_loss = 0.0
        with torch.inference_mode():
            for images, targets in loaders['val']: val_loss += nn.functional.cross_entropy(model(images.to(device)), targets.to(device)).item() * len(targets)
        val_loss /= len(loaders['val'].dataset); print(f'epoch={epoch + 1} train_loss={running / len(loaders["train"].dataset):.4f} val_loss={val_loss:.4f}', flush=True)
        if val_loss < best: best, best_state = val_loss, {key: value.detach().cpu() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state); torch.save(model.state_dict(), output_dir / 'plant_disease_model_efficientnet_b0.pth')
    metrics = {}; _, val_conf, val_correct = evaluate(model, loaders['val'], device, classes, output_dir, 'validation'); metrics['test'], _, _ = evaluate(model, loaders['test'], device, classes, output_dir, 'test'); metrics['field'], _, _ = evaluate(model, loaders['field'], device, classes, output_dir, 'field')
    thresholds = {str(round(float(threshold), 2)): float(np.mean(val_correct[val_conf >= threshold])) if np.any(val_conf >= threshold) else None for threshold in np.arange(.50, .96, .05)}
    manifest = {'model_version': 'efficientnet-b0-pv38-plantdoc-v1', 'architecture': 'torchvision EfficientNet-B0 transfer learning', 'class_mapping': 'class_names.json', 'class_count': len(classes), 'input': {'width': 224, 'height': 224, 'preprocessing': 'ImageNet EfficientNet-B0 resize/crop, mean/std normalization'}, 'datasets': {'plantvillage_color': {'train': len(pv_train), 'validation': len(pv_val), 'test': len(pv_test), 'classes': 38}, 'plantdoc_field': {'train_mapped': len(field_train), 'held_out_test': len(field_test)}}, 'validation_threshold_accuracy': thresholds, 'metrics': metrics}
    (output_dir / 'model_manifest_efficientnet_b0.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__': main()

