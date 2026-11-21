# Track A: Vision Engine Usage Guide

This directory contains the complete Track A Vision and Severity subsystem for the Offline Crop Disease Assistant.

## Architecture & Modules

1. **`vision/quality.py` (`ImageQualityChecker`)**:
   - OpenCV-based pre-inference guard.
   - Detects blur (Laplacian variance), under/over exposure (brightness bounds), and foliage presence (HSV foliage/lesion pixel ratio).
   - Generates Contract 1 `quality.issues` (`blurry`, `too_dark`, `too_bright`, `no_leaf`).

2. **`vision/severity.py` (`SeverityEstimator`)**:
   - Two-stage segmentation in HSV/color spaces:
     - Extracts plant leaf area mask.
     - Identifies necrotic and chlorotic lesion tissue.
   - Computes lesion area ratio: `(lesion_pixels / leaf_pixels) * 100`.
   - Maps percentage into agronomy severity bands (`none`, `mild`, `moderate`, `severe`).

3. **`vision/model.py` (`CropDiseaseClassifier`)**:
   - MobileNetV3-Large / Small architecture with custom head matched to `labels.json`.
   - Integrated temperature scaling parameter for probability calibration.
   - Energy-score and Max-Softmax Probability (MSP) out-of-distribution (OOD) score computation.

4. **`vision/calibration.py`**:
   - Post-processing temperature scaling optimization via NLL loss.
   - Expected Calibration Error (ECE) metric computation across confidence bins.

5. **`vision/dataset.py`**:
   - Perceptual hash deduplication (`compute_dhash`, `deduplicate_dataset`) to prevent near-duplicate leakage between train and test sets.
   - Field-condition augmentations: RandomResizedCrop, ColorJitter, GaussianBlur, RandomErasing (Cutout), and Flips.

6. **`vision/pipeline.py` (`VisionPipeline`)**:
   - End-to-end engine orchestrating Quality Check -> Model Inference -> Severity Estimation.
   - Produces Contract 1 compliant JSON output for downstream Track B (Advisory) and Track C (Android App).

7. **`vision/export.py`**:
   - PyTorch to ExecuTorch `.pte` export workflow (`torch.export` -> ExecuTorch EXIR `to_edge` -> `.pte`).

## Verification & Testing

Run unit tests via:
```bash
pytest vision/test_vision.py -v
```
