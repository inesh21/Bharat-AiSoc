"""Model architecture definitions for Track A Vision Classifier (Task A6 & A8).

Uses MobileNetV3-Large or MobileNetV3-Small backbone with:
- Pretrained weights on ImageNet
- Custom classification head sized to len(labels)
- Temperature scaling parameter for probability calibration (Task A9)
- Out-of-distribution (OOD) score computation (MSP and Energy score)
"""

from typing import List, Optional, Tuple, Dict
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


class CropDiseaseClassifier(nn.Module):
    """MobileNetV3 backbone for on-device plant disease classification and calibration."""

    def __init__(
        self,
        num_classes: int,
        backbone: str = "mobilenet_v3_large",
        pretrained: bool = True,
        temperature: float = 1.0,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.backbone_name = backbone
        
        if backbone == "mobilenet_v3_large":
            weights = models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
            base_model = models.mobilenet_v3_large(weights=weights)
            in_features = base_model.classifier[0].in_features
            # Retain feature extractor
            self.features = base_model.features
            self.avgpool = base_model.avgpool
            self.classifier = nn.Sequential(
                nn.Linear(in_features, 512),
                nn.Hardswish(),
                nn.Dropout(p=0.2),
                nn.Linear(512, num_classes),
            )
        elif backbone == "mobilenet_v3_small":
            weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
            base_model = models.mobilenet_v3_small(weights=weights)
            in_features = base_model.classifier[0].in_features
            self.features = base_model.features
            self.avgpool = base_model.avgpool
            self.classifier = nn.Sequential(
                nn.Linear(in_features, 512),
                nn.Hardswish(),
                nn.Dropout(p=0.2),
                nn.Linear(512, num_classes),
            )
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        # Learnable / calibratable temperature parameter (Task A9)
        self.temperature = nn.Parameter(torch.ones(1) * temperature)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns raw uncalibrated logits."""
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        logits = self.classifier(x)
        return logits

    def forward_calibrated(self, x: torch.Tensor) -> torch.Tensor:
        """Returns temperature-scaled calibrated logits."""
        logits = self.forward(x)
        temp = torch.clamp(self.temperature, min=0.1, max=10.0)
        return logits / temp

    def predict_probabilities(self, x: torch.Tensor) -> torch.Tensor:
        """Returns calibrated probabilities after softmax."""
        scaled_logits = self.forward_calibrated(x)
        return F.softmax(scaled_logits, dim=-1)

    @staticmethod
    def compute_energy_score(logits: torch.Tensor, T: float = 1.0) -> torch.Tensor:
        """Computes Free Energy score for OOD detection (Task A8).
        Lower / negative energy indicates in-distribution; higher values indicate OOD.
        Energy(x; T) = -T * log(sum(exp(logits / T)))
        """
        return -T * torch.logsumexp(logits / T, dim=-1)


def create_model(
    num_classes: int,
    backbone: str = "mobilenet_v3_large",
    pretrained: bool = False,
    temperature: float = 1.0,
) -> CropDiseaseClassifier:
    """Helper factory function to instantiate model."""
    return CropDiseaseClassifier(
        num_classes=num_classes,
        backbone=backbone,
        pretrained=pretrained,
        temperature=temperature,
    )
