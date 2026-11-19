"""vision/train.py – MobileNetV3-Large training script for crop disease classification.

Phase 2.4 of the runbook.  Requires a GPU environment with CUDA.
Install dependencies in .venv-vision (separate from .venv-et):
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install pyyaml ruff black pytest

Usage (after prepare_data.py has built data/processed/manifest.csv):
    python vision/train.py --config vision/train_config.yaml

Outputs:
    models_src/vision_v1.pt      – best checkpoint (highest val macro-F1)
    vision/runs/<date>/           – logs (gitignored)
"""

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import models, transforms

try:
    import yaml
except ImportError:
    raise ImportError("Install pyyaml: pip install pyyaml")

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class TrainConfig:
    # Data
    manifest_csv: str = "data/processed/manifest.csv"
    labels_json: str = "labels.json"
    num_workers: int = 4

    # Model
    backbone: str = "mobilenet_v3_large"
    pretrained: bool = True
    num_classes: int = 19  # must match labels.json

    # Training
    seed: int = 42
    image_size: int = 224
    batch_size: int = 32
    stage1_epochs: int = 3     # freeze backbone, train head
    stage2_epochs: int = 20    # unfreeze all, fine-tune
    lr_head: float = 1e-3
    lr_backbone: float = 1e-4
    weight_decay: float = 1e-4
    label_smoothing: float = 0.1
    early_stopping_patience: int = 5

    # Output
    output_dir: str = "models_src"
    output_name: str = "vision_v1.pt"
    run_dir: str = "vision/runs"

    # Quick sanity run
    sanity_classes: Optional[List[str]] = None  # e.g. ["tomato__early_blight", "tomato__healthy", "unknown"]
    max_samples_per_class: Optional[int] = None  # None = use all


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(image_size: int, is_train: bool):
    """Augmentation pipeline for training and validation."""
    if is_train:
        return transforms.Compose([
            transforms.RandomResizedCrop(image_size, scale=(0.6, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.1),
            transforms.GaussianBlur(kernel_size=5, sigma=(0.1, 2.0)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.25, scale=(0.02, 0.1)),  # cutout proxy
        ])
    else:
        return transforms.Compose([
            transforms.Resize(int(image_size * 1.14)),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


def build_dataset(manifest_csv: str, split: str, cfg: TrainConfig):
    """Builds a dataset from the manifest CSV for the given split."""
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
            path, label = row["path"], row["label"]
            img = Image.open(path).convert("RGB")
            if self.transform:
                img = self.transform(img)
            return img, self.label_to_idx[label]

    # Read manifest
    rows = []
    with open(REPO_ROOT / manifest_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["split"] == split:
                rows.append(r)

    # Filter to sanity classes if set
    if cfg.sanity_classes:
        rows = [r for r in rows if r["label"] in cfg.sanity_classes]

    # Build label index (must match labels.json order)
    import json
    with open(REPO_ROOT / cfg.labels_json) as f:
        all_labels = json.load(f)
    if cfg.sanity_classes:
        all_labels = cfg.sanity_classes
    label_to_idx = {l: i for i, l in enumerate(all_labels)}

    # Cap samples per class
    if cfg.max_samples_per_class:
        from collections import defaultdict
        grouped: dict = defaultdict(list)
        for r in rows:
            grouped[r["label"]].append(r)
        rows = []
        for lbl, lrows in grouped.items():
            rows.extend(lrows[: cfg.max_samples_per_class])

    is_train = split == "train"
    transform = build_transforms(cfg.image_size, is_train)
    return ManifestDataset(rows, label_to_idx, transform), label_to_idx


def build_model(cfg: TrainConfig) -> nn.Module:
    """Builds MobileNetV3-Large with a custom classification head."""
    weights = models.MobileNet_V3_Large_Weights.IMAGENET1K_V1 if cfg.pretrained else None
    model = models.mobilenet_v3_large(weights=weights)
    # Replace the classifier head
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.Hardswish(inplace=True),
        nn.Dropout(0.3),
        nn.Linear(256, cfg.num_classes),
    )
    return model


def freeze_backbone(model: nn.Module) -> None:
    for param in model.features.parameters():
        param.requires_grad = False


def unfreeze_all(model: nn.Module) -> None:
    for param in model.parameters():
        param.requires_grad = True


def compute_class_weights(dataset) -> torch.Tensor:
    """Returns per-sample weights for WeightedRandomSampler."""
    from collections import Counter
    labels = [row["label"] for row in dataset.rows]
    counts = Counter(labels)
    total = sum(counts.values())
    class_w = {l: total / (len(counts) * c) for l, c in counts.items()}
    return torch.tensor([class_w[row["label"]] for row in dataset.rows], dtype=torch.float)


def evaluate_epoch(model: nn.Module, loader: DataLoader, device: torch.device, num_classes: int):
    """Computes accuracy and macro-F1 on a dataloader."""
    from sklearn.metrics import f1_score  # type: ignore

    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, lbls in loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            logits = model(imgs)
            preds = logits.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(lbls.cpu().numpy())

    acc = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_labels)
    macro_f1 = f1_score(all_labels, all_preds, average="macro", zero_division=0)
    return acc, macro_f1


def train(cfg: TrainConfig) -> None:
    set_seed(cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if not torch.cuda.is_available():
        print("WARNING: No CUDA detected. Training on CPU will be very slow. Use a GPU machine.")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / cfg.run_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = REPO_ROOT / cfg.output_dir / cfg.output_name

    # Datasets
    print("Loading datasets…")
    train_ds, label_to_idx = build_dataset(cfg.manifest_csv, "train", cfg)
    val_ds, _ = build_dataset(cfg.manifest_csv, "val", cfg)
    n_classes = len(label_to_idx)
    print(f"  train={len(train_ds)}, val={len(val_ds)}, classes={n_classes}")

    sample_weights = compute_class_weights(train_ds)
    sampler = WeightedRandomSampler(sample_weights, len(train_ds), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, sampler=sampler,
                              num_workers=cfg.num_workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                            num_workers=cfg.num_workers, pin_memory=True)

    # Model
    model = build_model(cfg)
    model.num_classes = n_classes  # attach for reference
    model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)

    best_f1 = 0.0
    no_improve = 0

    # ------- Stage 1: train head only -------
    print(f"\n=== Stage 1: head only ({cfg.stage1_epochs} epochs) ===")
    freeze_backbone(model)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=cfg.lr_head, weight_decay=cfg.weight_decay
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=cfg.stage1_epochs)

    for epoch in range(1, cfg.stage1_epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), lbls)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * len(imgs)
            n += len(imgs)
        scheduler.step()
        val_acc, val_f1 = evaluate_epoch(model, val_loader, device, n_classes)
        print(f"  Stage1 Epoch {epoch}/{cfg.stage1_epochs}: loss={total_loss/n:.4f}, val_acc={val_acc:.4f}, val_macroF1={val_f1:.4f}")

    # ------- Stage 2: full fine-tune -------
    print(f"\n=== Stage 2: full fine-tune ({cfg.stage2_epochs} epochs) ===")
    unfreeze_all(model)
    optimizer = torch.optim.AdamW([
        {"params": model.features.parameters(), "lr": cfg.lr_backbone},
        {"params": model.classifier.parameters(), "lr": cfg.lr_head},
    ], weight_decay=cfg.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=cfg.stage2_epochs)

    for epoch in range(1, cfg.stage2_epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), lbls)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item() * len(imgs)
            n += len(imgs)
        scheduler.step()
        val_acc, val_f1 = evaluate_epoch(model, val_loader, device, n_classes)
        print(f"  Stage2 Epoch {epoch}/{cfg.stage2_epochs}: loss={total_loss/n:.4f}, val_acc={val_acc:.4f}, val_macroF1={val_f1:.4f}")

        if val_f1 > best_f1:
            best_f1 = val_f1
            no_improve = 0
            os.makedirs(output_path.parent, exist_ok=True)
            torch.save({"model_state_dict": model.state_dict(), "label_to_idx": label_to_idx,
                        "config": cfg.__dict__, "best_val_f1": best_f1}, output_path)
            print(f"    -> New best (val_macroF1={best_f1:.4f}). Saved to {output_path}")
        else:
            no_improve += 1
            if no_improve >= cfg.early_stopping_patience:
                print(f"  Early stopping at epoch {epoch} (no improvement for {no_improve} epochs).")
                break

    print(f"\nTraining complete. Best val macro-F1: {best_f1:.4f}")
    print(f"Best checkpoint: {output_path}")
    print("Next step: run vision/evaluate.py --checkpoint models_src/vision_v1.pt")


def load_config(path: str) -> TrainConfig:
    with open(path) as f:
        d = yaml.safe_load(f)
    return TrainConfig(**{k: v for k, v in d.items() if k in TrainConfig.__dataclass_fields__})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="vision/train_config.yaml", help="YAML config path")
    args = parser.parse_args()

    if os.path.exists(args.config):
        cfg = load_config(args.config)
    else:
        print(f"Config not found at {args.config}, using defaults.")
        cfg = TrainConfig()

    train(cfg)
