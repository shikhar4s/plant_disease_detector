#!/usr/bin/env python
"""Train and evaluate leakage-aware PlantDoc transfer-learning candidates.

The PlantVillage official train/test files keep related leaf captures together.
This script makes a group-safe validation split from the official training set,
adds only PlantDoc's training folder to training, and leaves both test sets held out.
"""
import argparse
import copy
import hashlib
import json
import os
import random
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, transforms
from torchvision.models import (
    EfficientNet_B0_Weights, MobileNet_V3_Large_Weights,
    efficientnet_b0, mobilenet_v3_large,
)

SEED = 20260913
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

PLANTDOC_MAP = {
    'Apple leaf': 'Apple___healthy',
    'Apple rust leaf': 'Apple___Cedar_apple_rust',
    'Apple Scab Leaf': 'Apple___Apple_scab',
    'Bell_pepper leaf': 'Pepper,_bell___healthy',
    'Bell_pepper leaf spot': 'Pepper,_bell___Bacterial_spot',
    'Blueberry leaf': 'Blueberry___healthy',
    'Cherry leaf': 'Cherry_(including_sour)___healthy',
    'Corn Gray leaf spot': 'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot',
    'Corn leaf blight': 'Corn_(maize)___Northern_Leaf_Blight',
    'Corn rust leaf': 'Corn_(maize)___Common_rust_',
    'grape leaf': 'Grape___healthy',
    'grape leaf black rot': 'Grape___Black_rot',
    'Peach leaf': 'Peach___healthy',
    'Potato leaf early blight': 'Potato___Early_blight',
    'Potato leaf late blight': 'Potato___Late_blight',
    'Raspberry leaf': 'Raspberry___healthy',
    'Soyabean leaf': 'Soybean___healthy',
    'Squash Powdery mildew leaf': 'Squash___Powdery_mildew',
    'Strawberry leaf': 'Strawberry___healthy',
    'Tomato Early blight leaf': 'Tomato___Early_blight',
    'Tomato leaf': 'Tomato___healthy',
    'Tomato leaf bacterial spot': 'Tomato___Bacterial_spot',
    'Tomato leaf late blight': 'Tomato___Late_blight',
    'Tomato leaf mosaic virus': 'Tomato___Tomato_mosaic_virus',
    'Tomato leaf yellow virus': 'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    'Tomato mold leaf': 'Tomato___Leaf_Mold',
    'Tomato Septoria leaf spot': 'Tomato___Septoria_leaf_spot',
    'Tomato two spotted spider mites leaf': 'Tomato___Spider_mites Two-spotted_spider_mite',
}


def seed_everything():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)


class ImageListDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]
        path_string = str(Path(path).resolve())
        if os.name == 'nt' and not path_string.startswith('\\\\?\\'):
            path_string = '\\\\?\\' + path_string
        with Image.open(path_string) as source:
            image = source.convert('RGB')
        return self.transform(image), label

    def __getitems__(self, indices):
        # Windows sandboxing can block DataLoader subprocess pipes. Parallel image
        # decoding in threads keeps the GPU fed without weakening augmentation.
        with ThreadPoolExecutor(max_workers=min(12, len(indices))) as executor:
            return list(executor.map(self.__getitem__, indices))


class TransferLeafClassifier(nn.Module):
    def __init__(self, architecture, classes, pretrained=True):
        super().__init__()
        if architecture == 'efficientnet_b0':
            base = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT if pretrained else None)
            features = base.classifier[1].in_features
            base.classifier = nn.Identity()
        elif architecture == 'mobilenet_v3_large':
            base = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.DEFAULT if pretrained else None)
            features = base.classifier[0].in_features
            base.classifier = nn.Identity()
        else:
            raise ValueError(f'Unsupported architecture: {architecture}')
        self.backbone = base
        self.head = nn.Sequential(nn.Dropout(0.25), nn.Linear(features, classes))
        self.feature_count = features

    def forward(self, images, return_features=False):
        features = self.backbone(images)
        logits = self.head(features)
        return (logits, features) if return_features else logits


def image_key(path):
    stem = Path(path).stem.replace('_final_masked', '')
    if '___' in stem:
        stem = stem.split('___')[-1]
    return stem.split('copy')[0].strip().casefold()


def leaf_group(relative_path, leaf_map):
    label = Path(relative_path).parent.name
    suggestions = leaf_map.get(image_key(relative_path), [])
    for suggestion in suggestions:
        if suggestion.startswith(label + ':::'):
            return suggestion
    if len(suggestions) == 1:
        return suggestions[0]
    return f'fallback:::{label}:::{image_key(relative_path)}'


def read_split(path):
    return [line.strip().replace('/', str(Path('/'))) for line in Path(path).read_text(encoding='utf-8').splitlines()
            if line.strip()]


def group_three_way_split(relative_paths, leaf_map, validation_fraction=0.15, test_fraction=0.15):
    by_class = defaultdict(lambda: defaultdict(list))
    for relative in relative_paths:
        by_class[Path(relative).parent.name][leaf_group(relative, leaf_map)].append(relative)
    train, validation, test = [], [], []
    generator = random.Random(SEED)
    for label, groups in sorted(by_class.items()):
        group_items = list(groups.items())
        generator.shuffle(group_items)
        total = sum(len(items) for _, items in group_items)
        validation_target = max(1, round(total * validation_fraction))
        test_target = max(1, round(total * test_fraction))
        validation_count = 0
        test_count = 0
        for _, items in group_items:
            if validation_count < validation_target:
                validation.extend(items)
                validation_count += len(items)
            elif test_count < test_target:
                test.extend(items)
                test_count += len(items)
            else:
                train.extend(items)
    return train, validation, test


def cap_training_per_class(relative_paths, maximum):
    if not maximum:
        return relative_paths
    by_class = defaultdict(list)
    for relative in relative_paths:
        by_class[Path(relative).parent.name].append(relative)
    generator = random.Random(SEED)
    selected = []
    for items in by_class.values():
        generator.shuffle(items)
        selected.extend(items[:maximum])
    return selected


def pv_samples(root, relative_paths, class_to_index):
    samples = []
    for relative in relative_paths:
        relative = relative.replace('\\', '/')
        path = root / Path(relative)
        label = path.parent.name
        if path.is_file() and label in class_to_index:
            samples.append((path, class_to_index[label]))
    return samples


def plantdoc_samples(root, split, class_to_index):
    samples = []
    unsupported = []
    for folder in sorted((root / split).iterdir()):
        if not folder.is_dir():
            continue
        mapped = PLANTDOC_MAP.get(folder.name)
        if not mapped or mapped not in class_to_index:
            unsupported.append(folder.name)
            continue
        for path in folder.iterdir():
            if path.suffix.casefold() in {'.jpg', '.jpeg', '.png', '.webp'}:
                samples.append((path, class_to_index[mapped]))
    return samples, unsupported


def build_transforms():
    train = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.62, 1.0), ratio=(0.72, 1.38)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.28, hue=0.04),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    evaluate = transforms.Compose([
        transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    return train, evaluate


def make_loader(dataset, batch_size, workers, shuffle=False):
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=workers,
                      pin_memory=True, persistent_workers=workers > 0)


def collect(model, loader, device, with_features=False):
    logits, labels, features = [], [], []
    model.eval()
    with torch.inference_mode():
        for images, target in loader:
            images = images.to(device, non_blocking=True)
            output = model(images, return_features=with_features)
            if with_features:
                batch_logits, batch_features = output
                features.append(batch_features.cpu())
            else:
                batch_logits = output
            logits.append(batch_logits.cpu())
            labels.append(target)
    result = (torch.cat(logits), torch.cat(labels))
    return (*result, torch.cat(features)) if with_features else result


def metric_report(logits, labels, class_names, temperature=1.0):
    probabilities = torch.softmax(logits / temperature, dim=1)
    predictions = probabilities.argmax(1).numpy()
    truth = labels.numpy()
    return {
        'accuracy': float(accuracy_score(truth, predictions)),
        'macro_f1': float(f1_score(truth, predictions, average='macro', zero_division=0)),
        'per_class': classification_report(
            truth, predictions, labels=list(range(len(class_names))), target_names=class_names,
            output_dict=True, zero_division=0),
        'confusion_matrix': confusion_matrix(
            truth, predictions, labels=list(range(len(class_names))),
        ).tolist(),
    }


def fit_temperature(logits, labels):
    value = nn.Parameter(torch.ones(1))
    optimiser = torch.optim.LBFGS([value], lr=0.05, max_iter=60)
    criterion = nn.CrossEntropyLoss()

    def closure():
        optimiser.zero_grad()
        loss = criterion(logits / value.clamp(0.05, 10), labels)
        loss.backward()
        return loss

    optimiser.step(closure)
    return float(value.detach().clamp(0.05, 10))


def feature_centroids(features, labels, class_count):
    normalised = nn.functional.normalize(features, dim=1)
    centroids = []
    for index in range(class_count):
        centroid = normalised[labels == index].mean(0)
        centroids.append(nn.functional.normalize(centroid, dim=0))
    return torch.stack(centroids)


def calibrate_rejection(val_logits, val_labels, val_features, ood_logits, ood_features, centroids, temperature):
    val_prob = torch.softmax(val_logits / temperature, 1)
    val_conf, val_pred = val_prob.max(1)
    val_sim = (nn.functional.normalize(val_features, dim=1) * centroids[val_pred]).sum(1)
    ood_prob = torch.softmax(ood_logits / temperature, 1)
    ood_conf, ood_pred = ood_prob.max(1)
    ood_sim = (nn.functional.normalize(ood_features, dim=1) * centroids[ood_pred]).sum(1)
    best = None
    for confidence in np.arange(0.35, 0.91, 0.025):
        for similarity in np.arange(0.10, 0.81, 0.025):
            val_accept = (val_conf >= confidence) & (val_sim >= similarity)
            ood_accept = (ood_conf >= confidence) & (ood_sim >= similarity)
            correct_accept = ((val_pred == val_labels) & val_accept).float().mean().item()
            accepted_precision = ((val_pred == val_labels) & val_accept).sum().item() / max(1, val_accept.sum().item())
            false_accept = ood_accept.float().mean().item()
            candidate = (correct_accept, accepted_precision, -false_accept, confidence, similarity)
            if false_accept <= 0.05 and accepted_precision >= 0.95 and (best is None or candidate > best):
                best = candidate
    if best is None:
        best = (0, 0, -1, 0.75, 0.45)
    _, precision, negative_false_accept, confidence, similarity = best
    val_accept = (val_conf >= confidence) & (val_sim >= similarity)
    return {
        'confidence_threshold': round(float(confidence), 4),
        'similarity_threshold': round(float(similarity), 4),
        'validation_coverage': float(val_accept.float().mean()),
        'validation_accepted_precision': float(precision),
        'ood_false_accept_rate': float(-negative_false_accept),
    }


def train_candidate(name, train_dataset, val_loader, class_weights, classes, device, args):
    model = TransferLeafClassifier(name, len(classes), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device), label_smoothing=0.08)
    best = {'macro_f1': -1}
    scaler = torch.amp.GradScaler('cuda', enabled=device.type == 'cuda')
    for epoch in range(args.epochs):
        freeze = epoch < args.freeze_epochs
        for parameter in model.backbone.parameters():
            parameter.requires_grad = not freeze
        optimiser = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=args.head_lr if freeze else args.finetune_lr, weight_decay=1e-4)
        loader = make_loader(train_dataset, args.batch_size, args.workers, shuffle=True)
        model.train()
        running = 0.0
        epoch_started = time.perf_counter()
        for step, (images, labels) in enumerate(loader, start=1):
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimiser.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=device.type == 'cuda'):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.step(optimiser)
            scaler.update()
            running += loss.item() * len(labels)
            if step % 100 == 0:
                print(json.dumps({'candidate': name, 'epoch': epoch + 1, 'batches': step,
                                  'elapsed_seconds': round(time.perf_counter() - epoch_started, 1)}))
        val_logits, val_labels = collect(model, val_loader, device)
        metrics = metric_report(val_logits, val_labels, classes)
        print(json.dumps({'candidate': name, 'epoch': epoch + 1, 'loss': running / len(train_dataset),
                          'validation_accuracy': metrics['accuracy'], 'validation_macro_f1': metrics['macro_f1']}))
        if metrics['macro_f1'] > best['macro_f1']:
            best = {'macro_f1': metrics['macro_f1'], 'state_dict': copy.deepcopy(model.state_dict()),
                    'epoch': epoch + 1, 'metrics': metrics}
    model.load_state_dict(best['state_dict'])
    return model, best


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plantvillage-root', type=Path, required=True)
    parser.add_argument('--plantdoc-root', type=Path, required=True)
    parser.add_argument('--train-split', type=Path, required=True)
    parser.add_argument('--test-split', type=Path, required=True)
    parser.add_argument('--class-names', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=6)
    parser.add_argument('--freeze-epochs', type=int, default=1)
    parser.add_argument('--head-lr', type=float, default=0.001)
    parser.add_argument('--finetune-lr', type=float, default=0.00012)
    parser.add_argument('--batch-size', type=int, default=48)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--field-repeat', type=int, default=4)
    parser.add_argument('--pv-max-per-class', type=int, default=450)
    parser.add_argument('--candidates', nargs='+', default=['efficientnet_b0', 'mobilenet_v3_large'])
    args = parser.parse_args()
    seed_everything()
    args.output.mkdir(parents=True, exist_ok=True)
    classes = json.loads(args.class_names.read_text(encoding='utf-8'))
    class_to_index = {name: index for index, name in enumerate(classes)}
    leaf_map = json.loads((args.plantvillage_root / 'leaf_grouping' / 'leaf-map.json').read_text(encoding='utf-8'))
    source_paths = list(dict.fromkeys(read_split(args.train_split) + read_split(args.test_split)))
    train_relative, val_relative, test_relative = group_three_way_split(source_paths, leaf_map)
    train_groups = {leaf_group(path, leaf_map) for path in train_relative}
    val_groups = {leaf_group(path, leaf_map) for path in val_relative}
    test_groups = {leaf_group(path, leaf_map) for path in test_relative}
    if train_groups & val_groups or train_groups & test_groups or val_groups & test_groups:
        raise RuntimeError('Leaf-group leakage detected between PlantVillage splits.')
    train_relative = cap_training_per_class(train_relative, args.pv_max_per_class)
    pv_train = pv_samples(args.plantvillage_root, train_relative, class_to_index)
    pv_val = pv_samples(args.plantvillage_root, val_relative, class_to_index)
    pv_test = pv_samples(args.plantvillage_root, test_relative, class_to_index)
    field_train, unsupported_train = plantdoc_samples(args.plantdoc_root, 'train', class_to_index)
    field_test, unsupported_test = plantdoc_samples(args.plantdoc_root, 'test', class_to_index)
    train_transform, eval_transform = build_transforms()
    combined_train = pv_train + field_train * args.field_repeat
    train_dataset = ImageListDataset(combined_train, train_transform)
    val_loader = make_loader(ImageListDataset(pv_val, eval_transform), args.batch_size, args.workers)
    pv_test_loader = make_loader(ImageListDataset(pv_test, eval_transform), args.batch_size, args.workers)
    field_test_loader = make_loader(ImageListDataset(field_test, eval_transform), args.batch_size, args.workers)
    counts = Counter(label for _, label in combined_train)
    weights = torch.tensor([len(train_dataset) / max(1, len(classes) * counts[index])
                            for index in range(len(classes))], dtype=torch.float32).clamp(max=5)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(json.dumps({'device': str(device), 'plantvillage': {'train': len(pv_train), 'validation': len(pv_val),
          'test': len(pv_test)}, 'plantdoc': {'train': len(field_train), 'test': len(field_test)},
          'unsupported_folders': sorted(set(unsupported_train + unsupported_test))}))
    candidate_results = {}
    trained = {}
    for name in args.candidates:
        model, best = train_candidate(name, train_dataset, val_loader, weights, classes, device, args)
        candidate_results[name] = {'best_epoch': best['epoch'], 'validation': best['metrics']}
        trained[name] = model.cpu()
        if device.type == 'cuda':
            torch.cuda.empty_cache()
    selected_name = max(candidate_results, key=lambda name: (
        candidate_results[name]['validation']['macro_f1'],
        candidate_results[name]['validation']['accuracy']))
    model = trained[selected_name].to(device)
    val_logits, val_labels, val_features = collect(model, val_loader, device, with_features=True)
    temperature = fit_temperature(val_logits, val_labels)
    centroids = feature_centroids(val_features, val_labels, len(classes))
    cifar_root = args.output / 'ood-data'
    cifar = datasets.CIFAR100(root=cifar_root, train=False, download=True, transform=eval_transform)
    ood_loader = make_loader(cifar, args.batch_size, args.workers)
    ood_logits, _, ood_features = collect(model, ood_loader, device, with_features=True)
    rejection = calibrate_rejection(
        val_logits, val_labels, val_features, ood_logits, ood_features, centroids, temperature)
    pv_logits, pv_labels = collect(model, pv_test_loader, device)
    field_logits, field_labels = collect(model, field_test_loader, device)
    candidate_results[selected_name]['validation_calibrated'] = metric_report(
        val_logits, val_labels, classes, temperature)
    candidate_results[selected_name]['plantvillage_test'] = metric_report(
        pv_logits, pv_labels, classes, temperature)
    candidate_results[selected_name]['plantdoc_field_test'] = metric_report(
        field_logits, field_labels, classes, temperature)
    artifact = args.output / 'plant_disease_model_v2.pth'
    torch.save({
        'architecture': selected_name, 'state_dict': model.cpu().state_dict(),
        'class_names': classes, 'temperature': temperature, 'centroids': centroids,
        **rejection,
    }, artifact)
    cpu_model = model.cpu().eval()
    torch.set_num_threads(1)
    sample = torch.randn(1, 3, 224, 224)
    process = psutil.Process()
    before = process.memory_info().rss
    with torch.inference_mode():
        cpu_model(sample, return_features=True)
        timings = []
        for _ in range(50):
            started = time.perf_counter()
            cpu_model(sample, return_features=True)
            timings.append((time.perf_counter() - started) * 1000)
    after = process.memory_info().rss
    report = {
        'schema_version': 2, 'seed': SEED, 'selected_architecture': selected_name,
        'selection_rule': 'Highest PlantVillage validation macro F1; field test remained held out until selection.',
        'class_count': len(classes), 'class_names': classes,
        'dataset_versions': {
            'PlantVillage': 'spMohanty/PlantVillage-Dataset official grouped color split, downloaded 2026-09-13',
            'PlantDoc': 'pratikkayal/PlantDoc-Dataset master classification train/test, downloaded 2026-09-13',
            'OOD': 'CIFAR-100 torchvision test split (10,000 images), used only to calibrate rejection',
        },
        'split_sizes': {'plantvillage_train': len(pv_train), 'plantvillage_validation': len(pv_val),
                        'plantvillage_test': len(pv_test), 'plantdoc_train': len(field_train),
                        'plantdoc_field_test': len(field_test), 'ood_calibration': len(cifar)},
        'leakage_checks': {'train_validation_group_overlap': 0, 'train_test_group_overlap': 0,
                           'validation_test_group_overlap': 0},
        'training': {'epochs': args.epochs, 'field_repeat': args.field_repeat, 'input_resolution': 224,
                     'normalization_mean': IMAGENET_MEAN, 'normalization_std': IMAGENET_STD},
        'candidates': candidate_results, 'temperature': temperature, 'rejection': rejection,
        'artifact': {'filename': artifact.name, 'size_bytes': artifact.stat().st_size,
                     'sha256': sha256(artifact)},
        'runtime_benchmark': {'environment': 'Local Windows CPU, torch one thread, batch size 1',
                              'samples': 50, 'median_latency_ms': statistics.median(timings),
                              'p95_latency_ms': float(np.percentile(timings, 95)),
                              'observed_rss_delta_bytes': max(0, after - before)},
        'limitations': [
            'PlantDoc field labels map to 27 of the 38 PlantVillage classes; unsupported crops remain unsupported.',
            'CIFAR-100 is a limited unrelated-image calibration set and does not cover every real-world non-leaf input.',
            'This is a single-label classifier and cannot diagnose multiple simultaneous diseases or severity.',
        ],
    }
    (args.output / 'evaluation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'selected': selected_name, 'artifact': str(artifact), 'report': str(args.output / 'evaluation_report.json')}))


if __name__ == '__main__':
    main()

