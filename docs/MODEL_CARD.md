# PlantDoc model card

## Deployed model

- Version: `legacy-cnn-pv38-v1`
- Architecture: custom residual CNN (`3→64→128→256→512` channels, 6,594,222 state parameters, 38-way linear head)
- Weights: `deployment_artifacts/plant_disease_model.pth`
- SHA-256: `18451c4ba8262edbda24ef91954945d9b3da92db40f5b0a3cad9ef92b7439a86`
- File size: 26,396,688 bytes (25.17 MiB)
- Input: 256 × 256 RGB; bilinear resize; values divided by 255 into `[0, 1]`; no additional mean/std normalisation
- Output: one class only. The model is not multilabel and cannot claim simultaneous diseases.
- Display uncertainty rule: top confidence below 0.70. This is a legacy heuristic, not a calibrated threshold.

The authoritative machine-readable version is `deployment_artifacts/model_manifest.json`; the ordered class mapping is `deployment_artifacts/class_names.json`.

## Measured runtime

On the local Windows CPU environment (Python 3.12, PyTorch 2.7.1 CPU, one Torch thread), 50 inferences after one warm-up measured a 1,080.33 ms median and 1,225.71 ms p95. The observed process RSS increase from before model construction to after inference was 57,896,960 bytes. This is an observed process delta, not allocator-isolated peak memory and not a Render-host measurement.

## Accuracy and generalisation status

Validation accuracy, held-out test accuracy, precision, recall, macro F1, per-class metrics and a confusion matrix are **not available**. The repository contains no labelled evaluation set, original split, duplicate-group manifest, training log or dataset version. Five historical uploads exist, but they are not labelled ground truth and cannot support an accuracy calculation.

Because no comparable evaluation is possible, this upgrade does not replace the weights with an unevaluated download and does not claim improved disease accuracy. MobileNetV3, EfficientNet-B0, ResNet-18 and DenseNet-121 remain reasonable transfer-learning candidates, but selection requires the same leakage-controlled train/validation/test and field-test protocol.

## Required replacement protocol

1. Obtain a specifically versioned dataset with its licence and citation. PlantVillage contains the broad 38-class laboratory-style label space; the PlantDoc field-image dataset provides more realistic imagery but a narrower and partly incompatible taxonomy.
2. Build a canonical label reconciliation table. Unsupported or ambiguous PlantDoc labels must not be silently forced into PlantVillage classes.
3. Hash perceptual and exact duplicates before splitting. Group related originals, derived crops and augmented versions so no group crosses train, validation or test boundaries.
4. Reserve a held-out test set before architecture selection. Use validation only for architecture, early stopping, temperature scaling and rejection thresholds.
5. Train the candidate architectures with architecture-appropriate preprocessing and realistic augmentation. Measure class-balanced metrics, per-class results, confusion matrices, field-image generalisation, file size, latency and peak memory.
6. Test unrelated, non-leaf, unsupported and poor-quality images. A separate out-of-distribution or leaf-quality mechanism is required; softmax confidence alone is insufficient.
7. Replace the production artifact only if accuracy, field performance, class coverage, latency and memory jointly improve within the hosting limit. Recheck numerical equivalence after ONNX or quantisation.

## Candidate datasets reviewed

- PlantVillage: Mohanty, Hughes and Salathé, “Using Deep Learning for Image-Based Plant Disease Detection,” Frontiers in Plant Science 7 (2016), DOI 10.3389/fpls.2016.01419. The public dataset is commonly described as roughly 54,303 images in 38 classes; exact release and licensing must be recorded at acquisition time.
- PlantDoc: Singh et al., “PlantDoc: A Dataset for Visual Plant Disease Detection,” CoDS-COMAD 2020, DOI 10.1145/3371158.3371196. Its official repository describes 2,598 field-style images across 13 plant species and up to 17 disease classes, licensed CC BY 4.0.

## Safety and limitations

The API rejects unreadable, oversized, extreme-brightness and almost detail-free images before inference. This is only an image-quality gate, not a validated leaf detector. For every accepted image the classifier still chooses among its 38 classes. Confidence is not severity, treatment certainty or proof that the upload is supported. Serious or spreading crop problems require professional agricultural advice.
