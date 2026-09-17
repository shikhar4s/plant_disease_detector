# Model audit, 15 September 2026

The previous EfficientNet release did not deploy: Render rejected a shell script
containing CRLF line endings. The live service was still on commit `6be9da4`.
Furthermore, inference could load the legacy checkpoint while returning the
EfficientNet manifest. Selection is now explicit and checksum-verified.

The earlier training report is **not sufficient evidence for promotion**:

- Its PlantDoc mapping excluded compatible labels and mapped some unrecognised
  conditions to healthy. The new mapping is explicit and rejects unknown folders.
- Exact-byte deduplication did not account for related captures of the same leaf.
- The stated 0.80 threshold was not calibrated against a separate field validation
  set. Laboratory selective accuracy does not establish field or non-leaf safety.
- Previous in-process memory observations were not production peak measurements.

Do not quote the older JSON metrics as independent, leakage-controlled evidence
of realistic phone-image accuracy. They remain in the repository as historical
artifacts, not as acceptance criteria or verified production metrics.

## New experiment

`scripts/train_field_candidate.py` uses an ImageNet-initialized EfficientNet-B0,
the repository's ordered 38-class registry, explicit PlantDoc mappings, official
PlantVillage leaf groups, exact decoded pixels and dHash distance <=4 grouping.
Groups related to the official PlantDoc test set are excluded from training and
validation. Augmentation happens only after the split. Perceptual hashing cannot
guarantee detecting all crops or transformed duplicates.

Measured split preparation: 56,877 source images; 222 test-related exclusions;
570 near-duplicate pairs; no split-group overlap. The bounded training subset is
7,520 PlantVillage + 1,700 PlantDoc images (field examples repeated during
training). Separate validation: 5,543 PlantVillage + 437 PlantDoc. Test: 5,303
PlantVillage + 236 official PlantDoc test images. Field test images may share a
source within that test set, so image-level metrics are not independent subjects.

Checkpoint selection uses validation only. Temperature and acceptance thresholds
use field validation, never test labels. Test metrics, class-level results,
confusion matrices and accepted coverage are exported after selection. Feature
similarity rejection is experimental, **not a validated non-leaf detector**.

No additional disease classes are invented. More classes require appropriately
labelled, licensed data and independent evaluation. The replacement was selected
after evaluation; production verification remains a separate step.

## Completed candidate evaluation

Selected epoch: 5 of 7, chosen using validation only. Architecture: EfficientNet-B0.

| Split | Images | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| PlantVillage validation | 5,543 | 97.11% | 96.13% | 97.01% | 96.38% |
| PlantVillage test | 5,303 | 97.79% | 97.08% | 97.77% | 97.32% |
| PlantDoc validation | 437 | 70.71% | 67.26% | 66.79% | 66.17% |
| PlantDoc test | 236 | 65.25% | 67.10% | 65.63% | 64.60% |

Field test crop identity accuracy is 79.66%. These results are not a claim of
65% accuracy on every user's phone images. Class-level metrics and confusion
matrices are in `deployment_artifacts/field_v2_evaluation.json` (macro scope:
classes with ground-truth support in each split).

Validation fitted temperature: 1.036494; confidence threshold: 0.825; predicted
class centroid cosine-similarity threshold: 0.4. Field validation acceptance:
192/437, 90.10% correct. Field test acceptance: 85/236 (36.02%), 85.88% correct,
12 confident mistakes. Rejected images receive an uncertain result. Similarity
does not prove an image is a leaf.

On these corrected field test labels, the legacy CNN scored 16.10% accuracy /
13.06% macro F1; the un-deployed v1 EfficientNet scored 41.53% / 37.15%. Old-model
training exposure is not known, so these are regression comparisons, not clean
independent generalisation estimates for the old weights.

Checkpoint: 16,722,568 bytes. Separate CPU-only Windows process (torch 2.7.1+cpu,
one thread, batch 1, preprocessing included, 5 warm-ups + 30 samples): median
289.40 ms, p95 354.77 ms, peak process RSS 357,113,856 bytes (340.57 MiB).
This is not a Render measurement. The training report peak includes training
allocations; use `field_v2_runtime.json` for the isolated inference benchmark.

The supplied portrait, solid green input and random noise were rejected in
three smoke checks. This tiny test is not a validated OOD benchmark; separate
unsupported-crop/non-leaf data remains required. No class expansion was made.

Sources: [PlantDoc dataset and CC BY 4.0 licence](https://github.com/pratikkayal/PlantDoc-Dataset),
[PlantVillage dataset and leaf grouping](https://github.com/spMohanty/PlantVillage-Dataset).

