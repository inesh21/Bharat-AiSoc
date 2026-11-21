"""End-to-end Vision Pipeline Engine (Contract 1 compliant).

Integrates:
1. Quality Checker (OpenCV blur, brightness, leaf ratio)
2. Vision Classifier (MobileNetV3 top-3, calibrated confidences, OOD/unknown detection)
3. Severity Estimator (lesion ratio & agronomy bands)
Emits structured JSON conforming to Contract 1 in docs/CONTRACTS.md.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
import cv2
import numpy as np
import torch
from PIL import Image

from vision.quality import ImageQualityChecker
from vision.severity import SeverityEstimator
from vision.model import CropDiseaseClassifier, create_model
from vision.dataset import get_field_transforms


class VisionPipeline:
    """Full offline vision pipeline emitting Contract 1 output."""

    def __init__(
        self,
        labels_path: str = "labels.json",
        model_version: str = "vision_v1",
        model: Optional[CropDiseaseClassifier] = None,
        device: str = "cpu",
        unknown_score_threshold: float = 5.0,  # Energy score threshold for OOD
        min_confidence_threshold: float = 0.35,
    ):
        self.model_version = model_version
        self.device = torch.device(device)
        self.unknown_score_threshold = unknown_score_threshold
        self.min_confidence_threshold = min_confidence_threshold

        with open(labels_path, "r", encoding="utf-8") as f:
            self.labels: List[str] = json.load(f)

        self.quality_checker = ImageQualityChecker()
        self.severity_estimator = SeverityEstimator()
        self.transforms = get_field_transforms(is_train=False)

        if model is not None:
            self.model = model.to(self.device)
            self.model.eval()
        else:
            # Default initialized model if no checkpoint provided
            self.model = create_model(num_classes=len(self.labels), pretrained=False).to(self.device)
            self.model.eval()

    def _determine_type(self, label: str) -> str:
        """Maps label to Contract 1 type: disease | pest | deficiency | healthy."""
        if label.endswith("__healthy"):
            return "healthy"
        if label.startswith("pest__"):
            return "pest"
        if "deficiency" in label:
            return "deficiency"
        return "disease"

    def _extract_crop(self, top_label: str) -> str:
        """Extracts crop name from label (e.g. 'tomato__early_blight' -> 'tomato')."""
        if "__" in top_label:
            return top_label.split("__")[0]
        return "unknown"

    def analyze(self, image_input, image_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes an image and returns full Contract 1 JSON dictionary.

        Args:
            image_input: image file path (str) or BGR numpy array (np.ndarray)
            image_id: optional UUID or identifier string

        Returns:
            Contract 1 compliant dictionary.
        """
        img_id = image_id or str(uuid.uuid4())

        # Load image
        if isinstance(image_input, str):
            bgr = cv2.imread(image_input)
            if bgr is None:
                return {
                    "schema_version": "1.0",
                    "image_id": img_id,
                    "model_version": self.model_version,
                    "quality": {"ok": False, "issues": ["corrupt_or_unreadable"]},
                    "unknown": True,
                    "crop": "unknown",
                    "predictions": [],
                    "severity": None,
                }
            rgb_pil = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            bgr = image_input
            rgb_pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        else:
            raise ValueError(f"Unsupported image_input type: {type(image_input)}")

        # 1. Quality Check (Task A10)
        quality_res = self.quality_checker.assess(bgr)
        quality_output = {
            "ok": quality_res["ok"],
            "issues": quality_res["issues"]
        }

        # If image quality fails significantly, we return early as per Contract 1
        if not quality_res["ok"]:
            return {
                "schema_version": "1.0",
                "image_id": img_id,
                "model_version": self.model_version,
                "quality": quality_output,
                "unknown": True,
                "crop": "unknown",
                "predictions": [],
                "severity": None,
            }

        # 2. Vision Model Inference (Task A6, A8, A9)
        tensor_in = self.transforms(rgb_pil).unsqueeze(0).to(self.device)
        with torch.no_grad():
            raw_logits = self.model(tensor_in)
            probs = self.model.predict_probabilities(tensor_in)[0]  # Calibrated probabilities
            energy_score = float(CropDiseaseClassifier.compute_energy_score(raw_logits)[0].item())

        # Top 3 predictions
        topk_probs, topk_indices = torch.topk(probs, k=min(3, len(self.labels)))
        predictions: List[Dict[str, Any]] = []

        is_unknown = False
        top_prob = float(topk_probs[0].item())
        top_label = self.labels[topk_indices[0].item()]

        # Check OOD or low confidence
        if top_label == "unknown" or top_prob < self.min_confidence_threshold:
            is_unknown = True

        for prob, idx in zip(topk_probs, topk_indices):
            lbl = self.labels[idx.item()]
            c_val = round(float(prob.item()), 2)
            c_type = self._determine_type(lbl)
            predictions.append({
                "label": lbl,
                "type": c_type,
                "confidence": c_val
            })

        crop_name = self._extract_crop(predictions[0]["label"]) if not is_unknown else "unknown"

        # 3. Severity Module (Task A11)
        # Severity is computed if not unknown and not a pest
        is_pest = predictions[0]["type"] == "pest" if predictions else False
        is_healthy = predictions[0]["type"] == "healthy" if predictions else False

        if is_unknown or is_pest:
            severity_data = None
        else:
            severity_res = self.severity_estimator.estimate(bgr, is_healthy=is_healthy)
            severity_data = {
                "percent": severity_res["percent"],
                "band": severity_res["band"]
            }

        return {
            "schema_version": "1.0",
            "image_id": img_id,
            "model_version": self.model_version,
            "quality": quality_output,
            "unknown": is_unknown,
            "crop": crop_name,
            "predictions": predictions,
            "severity": severity_data,
        }
