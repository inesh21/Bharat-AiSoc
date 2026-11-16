# Handoff: Track A: Vision and Severity

**Active agent:** none
**Owner (human):** ________
**Branch / worktree:** track-a/main  ->  ../crop-wt/track-a
**Task IDs:** A1 to A14 (see `docs/tracks/TRACK_A_VISION.md`)
**Last updated:** 2026-11-16

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
