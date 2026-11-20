# Handoff: Track A: Vision and Severity

**Active agent:** none
**Owner (human):** ________
**Branch / worktree:** track-a/main  ->  ../crop-wt/track-a
**Task IDs:** A1 to A14 (see `docs/tracks/TRACK_A_VISION.md`)
**Last updated:** 2026-11-20

## Milestone status

| Milestone | Status | Evidence |
|---|---|---|
| I0 Contracts frozen | in progress | `labels.json` and Contract 1 pipeline implemented |
| I1 Runtime proven | in progress | PyTorch 2.15 + CUDA 13.2 verified on Python 3.14 |
| I2 Vision on device | not started | |
| I3 Advisory on device | not started | |
| I4 End to end offline | not started | |
| I5 Voice and clarifications | not started | |
| I6 Freeze and polish | not started | |

## Requests to other tracks (open)

- To Track B: Defined 19 taxonomy classes in `labels.json` covering 5 crops (tomato, potato, rice, maize, cotton), pest (`pest__fall_armyworm`), and `unknown`. Please ground `knowledge/` entries using these IDs. | CONTRACTS.md Section 1 | needed for I0 | status: open
- To Track C: Vision pipeline produces Contract 1 compliant JSON. Preprocessing uses standard ImageNet normalization (mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225], 224x224 RGB). | CONTRACTS.md Section 2 | needed for I2 | status: open

## Requests from other tracks (handled)

- (none)

## Session log (newest first)

### Session 2026-11-20 17:50 | agent: antigravity | branch: integration
Task IDs: A4 (leakage prevention), A5 (data prep), dataset.md completion

**Summary**
Completed ingestion, deduplication, and preprocessing of all available dataset archives in `data/raw/` per `dataset.md`. Updated `vision/prepare_data.py`, `vision/class_map.yaml`, `docs/DATASETS.md`, and validated manifest with zero cross-split leakage.

**Done** (with evidence)
- `vision/prepare_data.py`: Updated with `--max-per-class` capping per split group (`train_val` vs `test`), and updated `FIELD_SOURCES` to ensure 100% field images route to the `test` split.
- `vision/class_map.yaml`: Mapped `rice_lab`, `riceleafbd_train`, `riceleafbd`, `cotton_lab`, and `mld_maize` subfolders to canonical taxonomy labels.
- Ingested Rice datasets:
  - `rice_lab`: Added 1,365 lab images (`rice__bacterial_blight`, `rice__blast`, `rice__brown_spot`). Deduplication eliminated near-duplicates; raw files and 7z cleaned up.
  - `riceleafbd`: Added 176 images to `riceleafbd_train` (`rice__healthy` in train/val) and 769 images to `riceleafbd` (test split: `rice__bacterial_blight`, `rice__brown_spot`, `rice__healthy`). Raw zip and folders cleaned up.
- Ingested Cotton dataset:
  - `cotton_lab`: Added 363 images (`cotton__bacterial_blight`, `cotton__healthy`) to train/val. Deduplicated and raw archive cleaned up.
- Ingested Maize dataset:
  - `mld_maize`: Extracted from `archive (1).zip`. Verified existing manifest already contains 600/class cap for maize train_val (`maize__northern_leaf_blight`, `maize__common_rust`, `maize__healthy`); raw archive and folders cleaned up.
- Verified `data/processed/manifest.csv`:
  - Total records: **9,531** (`train`: 6,851, `val`: 1,205, `test`: 1,475).
  - 17 of 19 classes populated. Zero leakage confirmed across sources (`plantvillage`, `rice_lab`, `riceleafbd_train`, `cotton_lab` only in train/val; `plantdoc`, `riceleafbd` strictly in test).
- Updated `docs/DATASETS.md` with full breakdown, licensing, and leakage prevention rules.

**Not done (data required)**
- Remaining 2 classes missing images: `pest__fall_armyworm` and `unknown` (non-plant images).
- `sar_cld_2024` (field cotton) was not present in `data/raw/`.

**Blockers**
- Need archives/images for `pest__fall_armyworm` (e.g. IP102 subset or Field Maize Leaf 8) and `unknown` (non-plant background captures).
- GPU environment: System has NVIDIA GeForce RTX 3050 Laptop GPU with CUDA 13.1 driver, and `C:\Python314\python.exe` has PyTorch 2.15.0+cu132, whereas `.venv-et` has CPU-only PyTorch. Full training should be launched using the CUDA Python environment or after installing CUDA PyTorch into a dedicated vision venv.

**Requests to other tracks / human**
- User/Human: Please provide images or archive for `pest__fall_armyworm` and `unknown` (non-leaf/random photos) to complete the 19-class training set.

---

### Session 2026-11-20 00:00 | agent: antigravity | branch: integration
Task IDs: A5 (data prep), A7 (training), A9 (evaluation)

**Summary**
Added training infrastructure scripts so Track A can proceed once datasets are downloaded.

**Done** (with evidence)
- `vision/prepare_data.py` – reads datasets from `data/raw/` using `class_map.yaml`, deduplicates via perceptual hash (dhash), assigns field-style sources (own_field, plantdoc) to `test` split, writes `data/processed/manifest.csv`.
- `vision/class_map.yaml` – source-folder → label mapping covering PlantVillage, rice leaf disease, cotton leaf, IP102 FAW, PlantDoc, and own-field photos.
- `vision/train.py` – MobileNetV3-Large two-stage training (Stage 1: head only 3 epochs; Stage 2: full fine-tune ≤25 epochs). Class-balanced sampling, label smoothing 0.1, cosine LR, early stopping, saves best val macro-F1 to `models_src/vision_v1.pt`.
- `vision/train_config.yaml` – default training config (19 classes, batch 32, etc.).
- `vision/evaluate.py` – accuracy, macro-F1, per-class P/R/F1, confusion matrix PNG, ECE, **field vs lab metrics separate** as required by runbook.

**Not done (data required)**
- Actual training cannot start until datasets are downloaded and placed in `data/raw/`.
- ExecuTorch export (`vision/export.py`) runs after a trained `models_src/vision_v1.pt` exists.
- Test vectors in `test_vectors/vision/` are generated post-export.

**Next steps**
1. **HUMAN**: Download datasets (see `docs/DATASETS.md` and `vision/class_map.yaml`) and place in `data/raw/<source>/`.
2. Run sanity check first (2–3 classes): uncomment `sanity_classes` in `vision/train_config.yaml`.
3. Run `python vision/prepare_data.py` → `python vision/train.py --config vision/train_config.yaml`.
4. Run `python vision/evaluate.py --checkpoint models_src/vision_v1.pt` and record metrics in this handoff.
5. Run calibration: `python vision/calibration.py` on val set.
6. Export: `python vision/export.py` (using `.venv-et` environment).
7. Generate test vectors and sidecar `models/vision_v1.json`.
8. Commit manifest entry for `vision_v1.pte` via `git add -f models/manifest.json`.

### Session 2026-11-16 18:05 | agent: antigravity | branch: track-a
Task IDs: A1, A2, A3, A4, A6, A7, A8, A9, A10, A11, A12

**Summary**
Implemented Track A foundational vision architecture, dataset documentation, image quality checking, severity estimation, temperature calibration, and end-to-end Contract 1 pipeline.

**Done** (with evidence)
- Defined unified crop disease taxonomy in `labels.json` (19 classes across 5 priority crops + pest + unknown).
- Documented dataset licensing, leak-prevention splitting rules, and OOD strategy in `docs/DATASETS.md`.
- Implemented OpenCV-based `ImageQualityChecker` (`vision/quality.py`) for blur (Laplacian var), brightness, and leaf presence.
- Implemented `SeverityEstimator` (`vision/severity.py`) for lesion area percentage segmentation and agronomic band classification.
- Implemented MobileNetV3 classifier (`vision/model.py`) with calibrated logits and energy-score OOD detection.
- Implemented temperature scaling calibration and ECE calculation (`vision/calibration.py`).
- Implemented perceptual hash deduplication and field augmentations (`vision/dataset.py`).
- Implemented end-to-end `VisionPipeline` (`vision/pipeline.py`) strictly conforming to Contract 1 schema.
- Verified test suite | verified by: `python -m pytest vision/test_vision.py -v` -> 6 passed in 17.88s.

**In progress / not done**
- Model training on actual multi-gigabyte dataset weights and ExecuTorch `.pte` compilation on target Android toolchain.

**Next steps**
1. Track B to match `knowledge/` rules with `labels.json`.
2. Generate test vectors in `test_vectors/vision/`.
3. Export and quantize `.pte` with pinned ExecuTorch XNNPACK build.

**Decisions made**
- MobileNetV3 chosen as vision backbone for balance of latency and accuracy on mobile Arm.
- Free Energy score combined with calibrated softmax for robust OOD/unknown detection.

**Files touched**
- `labels.json`
- `docs/DATASETS.md`
- `vision/__init__.py`
- `vision/quality.py`
- `vision/severity.py`
- `vision/model.py`
- `vision/calibration.py`
- `vision/dataset.py`
- `vision/export.py`
- `vision/pipeline.py`
- `vision/README.md`
- `vision/test_vision.py`
- `docs/handoffs/track-a.md`

**How to verify**
- `python -m pytest vision/test_vision.py -v` -> expect 6 passed.

**Blockers**
- None.

**Requests to other tracks**
- To Track B: Check `labels.json` taxonomy and integrate with rules engine.

**Assumptions / could not verify**
- Full `.pte` compilation requires final Android NDK / ExecuTorch C++ runtime build in Track C milestone I2.

## Archive summary

(Compacted older sessions go here.)
