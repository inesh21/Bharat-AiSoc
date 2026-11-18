import pytest
import numpy as np
import cv2
import torch
import os
import json

from vision.quality import ImageQualityChecker
from vision.severity import SeverityEstimator
from vision.model import CropDiseaseClassifier, create_model
from vision.calibration import compute_ece, TemperatureScaler
from vision.dataset import deduplicate_dataset, get_field_transforms
from vision.pipeline import VisionPipeline


def test_quality_checker_clean_leaf():
    checker = ImageQualityChecker()
    # Synthetic clean green image (100x100)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [35, 150, 45]  # Green BGR
    # Add some texture so Laplacian variance is not 0
    noise = np.random.randint(0, 30, (100, 100, 3), dtype=np.uint8)
    img = cv2.add(img, noise)

    res = checker.assess(img)
    assert "metrics" in res
    assert res["metrics"]["leaf_area_ratio"] > 0.5


def test_quality_checker_blurry_and_dark():
    checker = ImageQualityChecker(blur_threshold=50.0, dark_threshold=30.0)
    # Extremely dark and uniform image
    img = np.zeros((100, 100, 3), dtype=np.uint8) + 5
    res = checker.assess(img)
    assert not res["ok"]
    assert "too_dark" in res["issues"]
    assert "blurry" in res["issues"]
    assert "no_leaf" in res["issues"]


def test_severity_estimator():
    estimator = SeverityEstimator()
    # Healthy case
    healthy_res = estimator.estimate(np.zeros((50, 50, 3), dtype=np.uint8), is_healthy=True)
    assert healthy_res["percent"] == 0.0
    assert healthy_res["band"] == "none"

    # Synthetic leaf with lesion
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [35, 140, 40]  # Green background (leaf)
    # Add brown necrotic lesion spot (30x30 = 9% of area)
    img[20:50, 20:50] = [10, 20, 40]  # Dark brown necrotic spot

    res = estimator.estimate(img, is_healthy=False)
    assert res["band"] in ["mild", "moderate", "severe"]
    assert res["percent"] > 0.0


def test_model_forward_and_calibration():
    model = create_model(num_classes=5, backbone="mobilenet_v3_small", pretrained=False)
    x = torch.randn(2, 3, 224, 224)
    logits = model(x)
    assert logits.shape == (2, 5)

    probs = model.predict_probabilities(x)
    assert probs.shape == (2, 5)
    # Sum of probabilities across classes should be close to 1.0
    assert torch.allclose(probs.sum(dim=-1), torch.ones(2), atol=1e-4)


def test_compute_ece():
    probs = torch.tensor([[0.9, 0.1], [0.8, 0.2], [0.6, 0.4]])
    labels = torch.tensor([0, 0, 1])
    ece = compute_ece(probs, labels, n_bins=5)
    assert 0.0 <= ece <= 1.0


def test_pipeline_contract_output(tmp_path):
    labels = ["tomato__healthy", "tomato__early_blight", "pest__fall_armyworm", "unknown"]
    labels_file = tmp_path / "test_labels.json"
    with open(labels_file, "w", encoding="utf-8") as f:
        json.dump(labels, f)

    model = create_model(num_classes=len(labels), backbone="mobilenet_v3_small", pretrained=False)
    pipeline = VisionPipeline(labels_path=str(labels_file), model=model, device="cpu")

    # Green test image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [35, 150, 45]

    result = pipeline.analyze(img, image_id="test-img-001")
    assert result["schema_version"] == "1.0"
    assert result["image_id"] == "test-img-001"
    assert "quality" in result
    assert "unknown" in result
    assert "crop" in result
    assert "predictions" in result
    assert len(result["predictions"]) <= 3
    for p in result["predictions"]:
        assert "label" in p
        assert "type" in p
        assert "confidence" in p
