"""Reproducible field-focused training; no inference from unrecognised labels.

Uses the official leaf identity groups plus exact pixels and 64-bit dHash near
duplicates (distance <= 4). Groups are global across both datasets. PlantDoc's
official test is retained, removing related groups from all training/validation.
This script deliberately never downloads or silently promotes a checkpoint.
"""
import argparse
import copy
import hashlib
import json
import os
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image, ImageOps
from sklearn.metrics import classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader
from torchvision import models, transforms

from train_model_v2 import PLANTDOC_MAP, ImageListDataset, leaf_group

SEED = 20260914


def safe(path):
    value = str(Path(path).resolve())
    return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value


def fingerprint(record):
    with Image.open(safe(record['path'])) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
        pixels = np.asarray(image.resize((9, 8)).convert('L'))
        bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
        dhash = sum(int(bit) << i for i, bit in enumerate(bits))
    return digest, dhash


def prepare(args, classes):
    cache = args.output / 'data_manifest.json'
    if cache.exists():
        return json.loads(cache.read_text(encoding='utf-8'))
    mapping = {name: i for i, name in enumerate(classes)}
    leaf_map = json.loads((args.data / 'PlantVillage-Dataset-master/leaf_grouping/leaf-map.json').read_text())
    records = []
    for path in sorted((args.data / 'PlantVillage-Dataset-master/raw/color').glob('*/*')):
        if path.parent.name in mapping and path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            records.append({'path': str(path.resolve()), 'label': mapping[path.parent.name], 'domain': 'pv',
                            'source_split': '', 'leaf': leaf_group(str(path), leaf_map)})
    for split in ('train', 'test'):
        for folder in sorted((args.data / 'PlantDoc-Dataset-master' / split).iterdir()):
            if not folder.is_dir():
                continue
            label = PLANTDOC_MAP.get(folder.name)
            if label not in mapping:
                raise ValueError(f'Unmapped PlantDoc folder: {folder.name}')
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
                    records.append({'path': str(path.resolve()), 'label': mapping[label], 'domain': 'field',
                                    'source_split': split, 'leaf': ''})
    print(json.dumps({'phase': 'fingerprinting', 'images': len(records)}), flush=True)
    parent = list(range(len(records)))

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a, b):
        parent[find(a)] = find(b)

    identity, exact, buckets = {}, {}, defaultdict(list)
    with ThreadPoolExecutor(max_workers=8) as pool:
        fingerprints = list(pool.map(fingerprint, records))
    near_pairs = 0
    for i, (record, (digest, dhash)) in enumerate(zip(records, fingerprints)):
        # Filename variants in PlantDoc represent crops from the same source.
        stem = re.sub(r'(?:[_-]?\d+|\(\d+\))$', '', Path(record['path']).stem.casefold())
        identity_key = record['leaf'] if record['domain'] == 'pv' else f'field:{stem}'
        if identity_key in identity:
            union(i, identity[identity_key])
        identity[identity_key] = i
        if digest in exact:
            union(i, exact[digest])
        exact[digest] = i
        candidates = set()
        # Five disjoint bit blocks guarantee candidates for Hamming distance <=4.
        for block, (offset, width) in enumerate(((0, 13), (13, 13), (26, 13), (39, 13), (52, 12))):
            key = (block, (dhash >> offset) & ((1 << width) - 1))
            candidates.update(buckets[key])
            buckets[key].append(i)
        for j in candidates:
            if (dhash ^ fingerprints[j][1]).bit_count() <= 4:
                union(i, j)
                near_pairs += 1
    for i, record in enumerate(records):
        record['group'] = find(i)
        record['sha256_pixels'] = fingerprints[i][0]
    test_groups = {r['group'] for r in records if r['domain'] == 'field' and r['source_split'] == 'test'}
    available = [r for r in records if r['group'] not in test_groups]
    groups = defaultdict(list)
    for record in available:
        groups[record['group']].append(record)
    generator = random.Random(SEED)
    grouped = list(groups.items())
    generator.shuffle(grouped)
    # Stratified by domain and label; entire duplicate/leaf groups stay together.
    pools = defaultdict(list)
    for group, items in grouped:
        field = [item for item in items if item['domain'] == 'field']
        anchor = field[0] if field else items[0]
        pools[(anchor['domain'], anchor['label'])].append((group, items))
    split_by_group = {}
    for (domain, _), values in pools.items():
        validation_target = max(1, round(len(values) * (0.20 if domain == 'field' else 0.10)))
        test_target = 0 if domain == 'field' else max(1, round(len(values) * 0.10))
        for i, (group, _) in enumerate(values):
            split_by_group[group] = 'validation' if i < validation_target else 'test' if i < validation_target + test_target else 'train'
    partitions = {f'{domain}_{split}': [] for domain in ('pv', 'field') for split in ('train', 'validation', 'test')}
    dropped = []
    for record in records:
        if record['group'] in test_groups:
            if record['domain'] == 'field' and record['source_split'] == 'test':
                partitions['field_test'].append(record)
            else:
                dropped.append(record)
        else:
            partitions[f"{record['domain']}_{split_by_group[record['group']]}"] .append(record)
    train = partitions['pv_train']
    by_class = defaultdict(list)
    for record in train:
        by_class[record['label']].append(record)
    partitions['pv_train'] = [r for values in by_class.values() for r in generator.sample(values, min(args.pv_cap, len(values)))]
    report = {'seed': SEED, 'partitions': partitions, 'excluded_test_related': len(dropped),
              'near_duplicate_pairs': near_pairs, 'source_count': len(records),
              'mapping': PLANTDOC_MAP, 'split_counts': {k: len(v) for k, v in partitions.items()},
              'checks': {'group_overlap': 0, 'perceptual_distance': 4}}
    group_sets = {split: {r['group'] for domain in ('pv', 'field') for r in partitions[f'{domain}_{split}']}
                  for split in ('train', 'validation', 'test')}
    assert not (group_sets['train'] & group_sets['validation'] or group_sets['train'] & group_sets['test'] or group_sets['validation'] & group_sets['test'])
    cache.write_text(json.dumps(report), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'partitions' and k != 'mapping'}), flush=True)
    return report


def forward(model, inputs):
    features = torch.flatten(model.avgpool(model.features(inputs)), 1)
    return model.classifier(features), features


def collect(model, loader, device):
    all_logits, all_labels, all_features = [], [], []
    model.eval()
    with torch.inference_mode():
        for images, labels in loader:
            logits, features = forward(model, images.to(device))
            all_logits.append(logits.cpu())
            all_features.append(features.cpu())
            all_labels.append(labels)
    return torch.cat(all_logits), torch.cat(all_labels), torch.cat(all_features)


def metrics(logits, labels, classes):
    predictions = logits.argmax(1).numpy()
    report = classification_report(labels.numpy(), predictions, labels=list(range(len(classes))),
                                   target_names=classes, output_dict=True, zero_division=0)
    present = sorted(set(labels.tolist()))
    per_present = classification_report(labels.numpy(), predictions, labels=present, output_dict=True, zero_division=0)['macro avg']
    crops = [name.split('___')[0] for name in classes]
    return {'count': len(labels), 'accuracy': float((logits.argmax(1) == labels).float().mean()),
            'macro_precision': per_present['precision'], 'macro_recall': per_present['recall'], 'macro_f1': per_present['f1-score'],
            'macro_scope': 'classes with ground-truth support in this split',
            'crop_accuracy': float(np.mean([crops[p] == crops[y] for p, y in zip(predictions, labels.tolist())])),
            'per_class': report, 'confusion_matrix': confusion_matrix(labels.numpy(), predictions, labels=list(range(len(classes)))).tolist()}


def selection(logits, labels, features, centroids, temperature, confidence, similarity):
    probabilities = torch.softmax(logits / temperature, 1)
    scores, predicted = probabilities.max(1)
    similarities = (nn.functional.normalize(features, dim=1) * centroids[predicted]).sum(1)
    accepted = (scores >= confidence) & (similarities >= similarity)
    correct = predicted == labels
    return {'count': len(labels), 'accepted': int(accepted.sum()), 'coverage': float(accepted.float().mean()),
            'accepted_accuracy': float(correct[accepted].float().mean()) if accepted.any() else None,
            'confident_errors': int((accepted & ~correct).sum())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=7)
    parser.add_argument('--pv-cap', type=int, default=200)
    parser.add_argument('--field-repeat', type=int, default=2)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    classes = json.loads((args.repo / 'plant_disease_detector/deployment_artifacts/class_names.json').read_text())
    data = prepare(args, classes)
    if args.prepare_only:
        return
    transform = models.EfficientNet_B0_Weights.DEFAULT.transforms()
    augment = transforms.Compose([transforms.RandomResizedCrop(224, scale=(.65, 1)), transforms.RandomHorizontalFlip(),
                                  transforms.RandomVerticalFlip(.15), transforms.RandomRotation(25),
                                  transforms.ColorJitter(.25, .25, .25, .035), transforms.ToTensor(),
                                  transforms.Normalize(transform.mean, transform.std), transforms.RandomErasing(p=.10)])
    partitions = data['partitions']

    def loader(records, training=False):
        return DataLoader(ImageListDataset([(r['path'], r['label']) for r in records], augment if training else transform),
                          batch_size=args.batch_size, shuffle=training, num_workers=0, pin_memory=True)

    train_records = partitions['pv_train'] + partitions['field_train'] * args.field_repeat
    train_loader = loader(train_records, True)
    loaders = {key: loader(values) for key, values in partitions.items() if values}
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    counts = Counter(r['label'] for r in train_records)
    weights = torch.tensor([len(train_records) / (len(classes) * counts[i]) for i in range(len(classes))]).sqrt().to(device)
    scaler = torch.amp.GradScaler('cuda', enabled=device.type == 'cuda')
    optimizer = torch.optim.AdamW(model.parameters(), lr=.00025, weight_decay=.0001)
    best, history = -1, []
    for epoch in range(args.epochs):
        start = time.perf_counter()
        for parameter in model.features.parameters():
            parameter.requires_grad = epoch > 0
        model.train()
        if epoch == 0:
            model.features.eval()
        loss_sum = 0
        for step, (images, labels) in enumerate(train_loader):
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=device.type == 'cuda'):
                loss = nn.functional.cross_entropy(model(images.to(device)), labels.to(device), weight=weights, label_smoothing=.04)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            loss_sum += loss.item() * len(labels)
            if (step + 1) % 100 == 0:
                print(json.dumps({'epoch': epoch + 1, 'batches': step + 1, 'seconds': round(time.perf_counter() - start)}), flush=True)
        field = collect(model, loaders['field_validation'], device)
        pv = collect(model, loaders['pv_validation'], device)
        fm, pm = metrics(*field[:2], classes), metrics(*pv[:2], classes)
        score = .7 * fm['macro_f1'] + .3 * pm['macro_f1']
        history.append({'epoch': epoch + 1, 'loss': loss_sum / len(train_records), 'field_validation_accuracy': fm['accuracy'],
                        'field_validation_macro_f1': fm['macro_f1'], 'pv_validation_accuracy': pm['accuracy'], 'selection_score': score,
                        'elapsed_seconds': time.perf_counter() - start})
        print(json.dumps(history[-1]), flush=True)
        if score > best:
            best = score
            torch.save({'state_dict': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, 'epoch': epoch + 1}, args.output / 'best.pth')
    checkpoint = torch.load(args.output / 'best.pth', map_location='cpu', weights_only=True)
    model.load_state_dict(checkpoint['state_dict'])
    collections = {key: collect(model, value, device) for key, value in loaders.items()}
    # Centroids come from training only, so validation similarities are honest.
    train_features = torch.cat([collections[key][2] for key in ('pv_train', 'field_train')])
    train_labels = torch.cat([collections[key][1] for key in ('pv_train', 'field_train')])
    normalised = nn.functional.normalize(train_features, dim=1)
    centroids = torch.stack([nn.functional.normalize(normalised[train_labels == i].mean(0), dim=0) for i in range(len(classes))])
    field = collections['field_validation']
    # Field validation is used for temperature and acceptance, never the test set.
    from train_model_v2 import fit_temperature
    temperature = fit_temperature(field[0].clone(), field[1])
    options = []
    for confidence in np.arange(.50, .991, .025):
        for similarity in (.2, .3, .4, .5, .6, .7, .8):
            result = selection(*field, centroids, temperature, float(confidence), similarity)
            if result['accepted'] >= 20 and result['accepted_accuracy'] >= .90:
                options.append((result['coverage'], confidence, similarity, result))
    selected = max(options, key=lambda item: item[0]) if options else (0, .995, .85, {})
    _, confidence, similarity, _ = selected
    summaries = {key: metrics(*value[:2], classes) for key, value in collections.items() if not key.endswith('_train')}
    rejection = {key: selection(*value, centroids, temperature, float(confidence), float(similarity))
                 for key, value in collections.items() if not key.endswith('_train')}
    model.cpu().eval()
    torch.set_num_threads(1)
    sample = torch.rand(1, 3, 224, 224)
    timings = []
    with torch.inference_mode():
        for i in range(35):
            start = time.perf_counter()
            model(sample)
            if i >= 5:
                timings.append((time.perf_counter() - start) * 1000)
    artifact = args.output / 'plant_disease_model_field_v2.pth'
    torch.save({'state_dict': model.state_dict(), 'class_names': classes, 'centroids': centroids,
                'temperature': temperature, 'confidence_threshold': float(confidence), 'similarity_threshold': float(similarity)}, artifact)
    report = {'model_version': 'efficientnet-b0-field-v2', 'architecture': 'torchvision EfficientNet-B0', 'seed': SEED,
              'class_count': len(classes), 'class_names': classes, 'selected_epoch': checkpoint['epoch'],
              'selection_rule': '0.7 field validation macro F1 + 0.3 PlantVillage validation macro F1',
              'dataset_versions': {'PlantVillage': 'spMohanty/PlantVillage-Dataset archive downloaded 2026-09-13; CC BY-SA 3.0',
                                   'PlantDoc': 'pratikkayal/PlantDoc-Dataset archive downloaded 2026-09-13; CC BY 4.0'},
              'split_counts': data['split_counts'], 'excluded_test_related': data['excluded_test_related'],
              'near_duplicate_pairs': data['near_duplicate_pairs'], 'checks': data['checks'], 'training': history,
              'metrics': summaries, 'temperature': temperature, 'uncertainty_threshold': float(confidence),
              'similarity_threshold': float(similarity), 'acceptance_metrics': rejection,
              'runtime': {'context': 'local Windows CPU, one Torch thread, warmed inference_mode, batch 1', 'samples': len(timings),
                          'median_ms': statistics.median(timings), 'p95_ms': float(np.percentile(timings, 95)),
                          'process_peak_rss_bytes': psutil.Process().memory_info().peak_wset},
              'artifact': {'filename': artifact.name, 'bytes': artifact.stat().st_size, 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()},
              'input': {'width': 224, 'height': 224, 'resize_short_edge': 256, 'crop': 'center', 'mean': transform.mean, 'std': transform.std},
              'limitations': ['No validated non-leaf detector; feature similarity adds an unvalidated rejection check.',
                              'No external unseen phone-image benchmark; PlantDoc is small, web-scraped and contains label noise.',
                              '38 single-label categories; no multilabel, severity or unsupported-crop diagnosis.',
                              'Near-duplicate hashing cannot guarantee finding heavily transformed or differently cropped copies.',
                              'Older production model was exposed to some current validation/test images; its evaluation is a regression comparison, not an independent held-out estimate.']}
    (args.output / 'evaluation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    # Persist raw held-out observations so calibration and errors can be audited.
    torch.save({key: {'logits': value[0], 'labels': value[1], 'features': value[2]} for key, value in collections.items() if not key.endswith('_train')}, args.output / 'observations.pth')
    print(json.dumps({'completed': True, 'metrics': {k: {n: v for n, v in m.items() if n not in ('per_class', 'confusion_matrix')} for k, m in summaries.items()}, 'acceptance': rejection}), flush=True)


if __name__ == '__main__':
    main()

