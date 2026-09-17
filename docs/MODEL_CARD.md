# PlantDoc model card

## Selected model and audit

Selection is explicit in `deployment_artifacts/selected_model.json`, with a SHA256 check before loading. The selected model is `efficientnet-b0-field-v2`: 38 classes, 224px RGB, resize short edge 256 and center crop, ImageNet normalization. No silent architecture fallback is allowed.

The previous v1 EfficientNet release did not deploy, and its old reports had label-mapping and duplicate-grouping limitations. Its claimed calibrated threshold and independent phone-image accuracy are withdrawn. See [EVALUATION_REVIEW.md](EVALUATION_REVIEW.md) for all measured v2 results, split sizes, runtime and acceptance/rejection limitations. Old v1 metric JSON files are historical artifacts, not evidence for promotion. The new model weights are released under CC BY-SA 3.0 with attribution to PlantVillage (Mohanty, Hughes and Salathé) and PlantDoc (Singh et al.); PyTorch/torchvision retain their own licences.

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

