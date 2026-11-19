"""vision/evaluate.py – Evaluation script for the trained vision model.

Phase 2.4 of the runbook.
Loads a checkpoint from models_src/vision_v1.pt and evaluates it on the
test split (field-style images), separately reporting lab vs field metrics
as required by the runbook.

Usage:
    python vision/evaluate.py --checkpoint models_src/vision_v1.pt \\
                              --manifest data/processed/manifest.csv \\
                              [--save_confusion vision/runs/confusion.png]

Outputs (printed + optionally saved):
    - Accuracy, macro-F1
    - Per-class precision/recall table
    - Confusion matrix image (if matplotlib installed)
    - ECE (Expected Calibration Error)
    - Lab vs Field metric comparison table
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_model_and_meta(checkpoint_path: str):
    """Loads the model from a checkpoint saved by train.py."""
    from torchvision import models
    import torch.nn as nn

    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    label_to_idx: Dict[str, int] = ckpt["label_to_idx"]
    num_classes = len(label_to_idx)

    model = models.mobilenet_v3_large(weights=None)
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(inplace=True),
        nn.Dropout(0.3),
        nn.Linear(256, num_classes),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model, label_to_idx, ckpt


def build_eval_transform(image_size: int = 224):
    return transforms.Compose([
        transforms.Resize(int(image_size * 1.14)),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def build_dataset(manifest_csv: str, split: str, label_to_idx: Dict[str, int]):
    import csv
    from PIL import Image

    class ManifestDataset(torch.utils.data.Dataset):
        def __init__(self, rows, label_to_idx, transform):
            self.rows = rows
            self.label_to_idx = label_to_idx
            self.transform = transform

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, idx):
            row = self.rows[idx]
            img = Image.open(row["path"]).convert("RGB")
            img = self.transform(img)
            lbl = self.label_to_idx.get(row["label"], -1)
            source = row.get("source", "unknown")
            return img, lbl, source

    rows = []
    with open(manifest_csv, newline="", encoding="utf-8") as f:
        import csv as csv_mod
        reader = csv_mod.DictReader(f)
        for r in reader:
            if r["split"] == split and r["label"] in label_to_idx:
                rows.append(r)

    transform = build_eval_transform()
    return ManifestDataset(rows, label_to_idx, transform)


def compute_ece(logits_all: np.ndarray, labels_all: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error (binned)."""
    probs = torch.softmax(torch.tensor(logits_all), dim=-1).numpy()
    confidences = probs.max(axis=1)
    preds = probs.argmax(axis=1)
    correct = (preds == labels_all).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bin_boundaries[:-1], bin_boundaries[1:]):
        mask = (confidences > lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        avg_confidence = confidences[mask].mean()
        avg_accuracy = correct[mask].mean()
        ece += mask.sum() * abs(avg_confidence - avg_accuracy)
    return float(ece / max(len(labels_all), 1))


def evaluate(
    model: torch.nn.Module,
    dataset,
    device: torch.device,
    label_to_idx: Dict[str, int]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """Runs inference and returns (all_logits, all_preds, all_labels, all_sources)."""
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=0)
    all_logits, all_preds, all_labels, all_sources = [], [], [], []

    model.eval()
    with torch.no_grad():
        for imgs, lbls, sources in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            preds = logits.argmax(dim=-1)
            all_logits.append(logits.cpu().numpy())
            all_preds.append(preds.cpu().numpy())
            all_labels.append(lbls.numpy())
            all_sources.extend(sources)

    return (
        np.concatenate(all_logits),
        np.concatenate(all_preds),
        np.concatenate(all_labels),
        all_sources,
    )


def print_metrics(
    logits: np.ndarray,
    preds: np.ndarray,
    labels: np.ndarray,
    idx_to_label: Dict[int, str],
    split_name: str,
    save_confusion: Optional[str] = None
) -> None:
    from sklearn.metrics import (  # type: ignore
        accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix
    )

    acc = accuracy_score(labels, preds)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    ece = compute_ece(logits, labels)

    print(f"\n{'=' * 60}")
    print(f"Split: {split_name}")
    print(f"  Samples : {len(labels)}")
    print(f"  Accuracy: {acc:.4f} ({acc * 100:.2f}%)")
    print(f"  Macro-F1: {macro_f1:.4f}")
    print(f"  ECE     : {ece:.4f}")

    # Per-class
    classes = sorted(idx_to_label.keys())
    p, r, f, s = precision_recall_fscore_support(labels, preds, labels=classes, zero_division=0)
    print(f"\n  {'Class':<35} {'P':>6} {'R':>6} {'F1':>6} {'N':>6}")
    print(f"  {'-' * 60}")
    for i, cls_idx in enumerate(classes):
        cls_name = idx_to_label[cls_idx]
        print(f"  {cls_name:<35} {p[i]:>6.3f} {r[i]:>6.3f} {f[i]:>6.3f} {int(s[i]):>6}")

    # Confusion matrix
    if save_confusion:
        try:
            import matplotlib  # type: ignore
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            cm = confusion_matrix(labels, preds, labels=classes)
            fig, ax = plt.subplots(figsize=(12, 10))
            im = ax.imshow(cm, cmap="Blues")
            ax.set_xticks(range(len(classes)))
            ax.set_yticks(range(len(classes)))
            ax.set_xticklabels([idx_to_label[i] for i in classes], rotation=45, ha="right", fontsize=7)
            ax.set_yticklabels([idx_to_label[i] for i in classes], fontsize=7)
            plt.colorbar(im)
            ax.set_title(f"Confusion Matrix – {split_name}")
            plt.tight_layout()
            os.makedirs(os.path.dirname(save_confusion) or ".", exist_ok=True)
            plt.savefig(save_confusion, dpi=120)
            plt.close()
            print(f"\n  Confusion matrix saved to {save_confusion}")
        except ImportError:
            print("  (matplotlib not installed; confusion matrix not saved)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="models_src/vision_v1.pt")
    parser.add_argument("--manifest", default="data/processed/manifest.csv")
    parser.add_argument("--split", default="test", help="Manifest split to evaluate (test, val, train)")
    parser.add_argument("--save_confusion", default="", help="Path to save confusion matrix PNG")
    args = parser.parse_args()

    checkpoint_path = str(REPO_ROOT / args.checkpoint) if not os.path.isabs(args.checkpoint) else args.checkpoint
    manifest_path = str(REPO_ROOT / args.manifest) if not os.path.isabs(args.manifest) else args.manifest

    print(f"Loading checkpoint: {checkpoint_path}")
    model, label_to_idx, ckpt = load_model_and_meta(checkpoint_path)
    idx_to_label = {v: k for k, v in label_to_idx.items()}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    print(f"Classes: {len(label_to_idx)}, best_val_f1={ckpt.get('best_val_f1', 'N/A')}")

    dataset = build_dataset(manifest_path, args.split, label_to_idx)
    print(f"Evaluating {len(dataset)} samples (split={args.split})…")

    logits, preds, labels, sources = evaluate(model, dataset, device, label_to_idx)

    # Overall metrics
    save_path = args.save_confusion if args.save_confusion else None
    print_metrics(logits, preds, labels, idx_to_label, split_name=f"{args.split} (all)", save_confusion=save_path)

    # Field vs lab breakdown (by source)
    # Assumption: "own_field" or "plantdoc" sources → field; others → lab
    field_sources = {"own_field", "plantdoc"}
    field_mask = np.array([s.lower() in field_sources for s in sources])
    lab_mask = ~field_mask

    if field_mask.sum() > 0:
        print_metrics(logits[field_mask], preds[field_mask], labels[field_mask], idx_to_label,
                      split_name=f"{args.split} (field only)")
    else:
        print("\n  NOTE: No field-source samples found in this split (plantdoc/own_field).")
        print("  Add own photos (runbook section 2.3b) for a meaningful field metric.")

    if lab_mask.sum() > 0:
        print_metrics(logits[lab_mask], preds[lab_mask], labels[lab_mask], idx_to_label,
                      split_name=f"{args.split} (lab only)")


if __name__ == "__main__":
    main()
