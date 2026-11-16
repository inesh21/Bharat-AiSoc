# Track A: Vision and Severity (agent brief)

**Mission:** turn an image into a trustworthy, calibrated, quantized prediction and a severity band, packaged so Track C can run it on the phone with no surprises.

**Owned paths:** `vision/`, `labels.json`, `test_vectors/vision/`, `docs/DATASETS.md`, `docs/handoffs/track-a.md`, your entries in `models/manifest.json`.

**Produces:** Contract 1 (vision result), `labels.json`, `models/vision_vX.pte` + `vision_vX.json`, test vectors, model card.
**Consumes:** nothing from other tracks except `docs/versions.md` (pinned ExecuTorch) and the Android preprocessing details from Track C.

## Tasks

- [ ] **A1** Download datasets (PlantVillage, a field-condition set such as PlantDoc, IP102 for pests, Cassava or region-relevant sets). Record source and license in `docs/DATASETS.md`.
- [ ] **A2** Define the taxonomy `crop__condition` and write `labels.json`; share with B and C early (Day 2).
- [ ] **A3** Clean data: deduplicate with perceptual hashing, remove corrupt files, fix labels.
- [ ] **A4** Split by source/plant/batch, not randomly per image (PlantVillage has near-duplicates, so random splits leak). Lock a final test set.
- [ ] **A5** Collect 100 to 300 real-world phone photos, including non-leaf images for the `unknown` class. Label carefully.
- [ ] **A6** Baseline: MobileNetV3-Large or EfficientNet-Lite, 224 to 256 px, ImageNet-pretrained, freeze then fine-tune, AdamW, cosine schedule, label smoothing 0.1, early stopping on validation macro-F1.
- [ ] **A7** Field-condition augmentation: crop, color jitter, blur, random backgrounds, cutout, mixup/cutmix. Handle class imbalance (weights or balanced sampling).
- [ ] **A8** `unknown` class plus out-of-distribution score (max-softmax or energy); choose the threshold on validation data.
- [ ] **A9** Calibration by temperature scaling; report Expected Calibration Error.
- [ ] **A10** Image quality checker with OpenCV: blur (variance of Laplacian), brightness, leaf-area presence. Output the `quality.issues` list.
- [ ] **A11** Severity: segment leaf, segment lesions, compute area ratio, map to bands per crop (bands from agronomy references). Validate against a small hand-labeled set.
- [ ] **A12** Export: PyTorch -> `torch.export` -> ExecuTorch (XNNPACK) `.pte`; int8 post-training quantization with 200 to 1000 calibration images; use quantization-aware training if accuracy drops more than 2 points.
- [ ] **A13** Verify exported model vs PyTorch on 50 images; commit as `test_vectors/vision/` with expected outputs and tolerance.
- [ ] **A14** Model card (`models/vision_vX.json` plus a short doc): input size, normalization, labels, metrics, thresholds, version, export command.

## Definition of done

- Agreed macro-F1 target met on the **field-style** test set (not only PlantVillage).
- Unknown/non-plant images are rejected at the agreed rate.
- Model size within the agreed limit.
- Output of the exported model matches PyTorch within tolerance, and Track C confirmed it on the phone (milestone I2).
- Metrics reported: accuracy, macro-F1, per-class results, confusion matrix, field-only results, ECE, quantization drop.

## Integration points

- **To Track C:** `.pte`, sidecar JSON, test vectors, manifest entry (see `HANDOFF.md` section 7). Preprocessing lives in the sidecar JSON.
- **To Track B:** `labels.json` and a few realistic vision JSON samples (also placed in `mocks/` via the shared process).
- **From Track C:** device constraints (RAM, latency budget) that may limit model size.

## Stretch (only after I4)

Pest detection with a nano detector; nutrient deficiency classes; Hailo HEF compile for the Pi (vision via HailoRT, kept as a separate pipeline from Llama).

## Watch-outs

- Lab-background accuracy does not predict field accuracy. Always report both.
- Never tune on the locked test set.
- Preprocessing mismatch with the app is the most common integration bug.
