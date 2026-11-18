"""Temperature scaling calibration and evaluation (Task A9).

Provides:
- TemperatureScaler: post-processing calibration on validation set
- Expected Calibration Error (ECE) metric computation
"""

from typing import Tuple
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np


def compute_ece(probs: torch.Tensor, labels: torch.Tensor, n_bins: int = 15) -> float:
    """Computes Expected Calibration Error (ECE).

    Args:
        probs: (N, C) softmax probabilities tensor
        labels: (N,) ground-truth class indices tensor
        n_bins: number of confidence bins

    Returns:
        ece: scalar Expected Calibration Error
    """
    confidences, predictions = torch.max(probs, dim=1)
    accuracies = predictions.eq(labels)

    bin_boundaries = torch.linspace(0, 1, n_bins + 1)
    ece = torch.zeros(1, device=probs.device)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = in_bin.float().mean()

        if prop_in_bin.item() > 0:
            accuracy_in_bin = accuracies[in_bin].float().mean()
            avg_confidence_in_bin = confidences[in_bin].mean()
            ece += torch.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece.item())


class TemperatureScaler(nn.Module):
    """Post-processing calibration module using Temperature Scaling (Guo et al. 2017)."""

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """Scales logits by 1/T."""
        temp = torch.clamp(self.temperature, min=0.01, max=10.0)
        return logits / temp

    def fit(self, val_logits: torch.Tensor, val_labels: torch.Tensor, max_iter: int = 50) -> float:
        """Optimizes temperature T using L-BFGS or Adam on validation NLL."""
        self.temperature.data.fill_(1.5)
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=0.01, max_iter=max_iter)

        def eval_step():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            loss.backward()
            return loss

        optimizer.step(eval_step)
        return float(self.temperature.item())
