# PlantDoc model card

## Active model

- Version: `efficientnet-b0-pv38-plantdoc-v1`
- Architecture: torchvision EfficientNet-B0 transfer learning with a 38-way head
- Weights: `deployment_artifacts/plant_disease_model_efficientnet_b0.pth` (16,533,943 bytes / 15.77 MiB)
- Input: 224 × 224 RGB; EfficientNet resize/crop; ImageNet mean/std normalisation
- Output: one class only. The model is not multilabel and cannot claim simultaneous diseases.
- Uncertainty rule: top confidence below 0.80 is shown as uncertain. This threshold is calibrated against PlantVillage validation confidence; it is not a validated leaf detector and is not disease severity.

The authoritative machine-readable version is `deployment_artifacts/model_manifest_efficientnet_b0.json`; the ordered class mapping is `deployment_artifacts/class_names.json`.

## Measured runtime

On the local Windows CPU environment (Python 3.12, PyTorch 2.7.1, one Torch thread), a warmed single-image benchmark was approximately 150 ms per inference. This is a local observation; Render memory and latency must be checked after deployment. The service keeps a legacy-CNN fallback if the candidate artifact is absent.

## Accuracy and generalisation

PlantVillage color split (38 classes): 43,447 train / 5,428 validation / 5,430 held-out test. Exact-byte duplicate groups were kept in one split. PlantDoc contributed 1,825 mapped training images and 183 held-out field images; incompatible labels were excluded rather than silently remapped.

| Evaluation | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| PlantVillage validation | 87.29% | 82.58% | 86.68% | 83.36% |
| PlantVillage test | 86.96% | 81.98% | 86.17% | 83.12% |
| PlantDoc field test | 49.73% | 27.15% | 26.87% | 25.10% |
| Legacy CNN, same field test | 12.02% | 9.22% | 7.50% | 7.20% |

Per-class reports and confusion matrices are stored in `validation_metrics.json`, `test_metrics.json` and `field_metrics.json`. The field score is substantially better than the legacy baseline but still demonstrates domain shift; the UI therefore preserves conservative uncertainty messaging and the agricultural disclaimer.

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

