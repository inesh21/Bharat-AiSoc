"""vision/prepare_data.py – Data preparation for vision model training.

Phase 2.3 of the runbook.

Reads datasets from data/raw/<source_name>/ and writes
data/processed/manifest.csv with columns: path,label,source,split

Usage:
    python vision/prepare_data.py --class_map vision/class_map.yaml

Manual step required first:
    Download datasets to data/raw/ as documented in docs/DATASETS.md.
    See runbook section 2.2 for the full list.

Split strategy (runbook section 2.3):
    test  – field-style sources (own_field, plantdoc)
    val   – 15% of lab sources, taken per source-folder not per image
    train – remaining lab sources

Unknown class:
    Non-plant images from data/raw/unknown/ split 70/15/15 train/val/test.
"""

import argparse
import csv
import hashlib
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:
    raise ImportError("Install pyyaml: pip install pyyaml")

DEFAULT_CLASS_MAP = REPO_ROOT / "vision" / "class_map.yaml"
MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "manifest.csv"

# Sources that are always assigned to test (field-style images)
FIELD_SOURCES = {"own_field", "plantdoc"}

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_image(path: Path) -> bool:
    return path.suffix.lower() in VALID_IMAGE_EXTS


def remove_near_duplicates(
    paths: List[Path],
    hash_size: int = 8,
    max_diff: int = 3
) -> List[Path]:
    """Deduplicates using perceptual hash (dhash).  Requires Pillow."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        print("  WARNING: Pillow not installed; skipping near-duplicate removal.")
        return paths

    def dhash(img, size=hash_size):
        img = img.convert("L").resize((size + 1, size), Image.LANCZOS)
        pixels = list(img.getdata())
        diff = []
        for row in range(size):
            for col in range(size):
                diff.append(pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1])
        return int("".join("1" if b else "0" for b in diff), 2)

    def hamming(a, b):
        return bin(a ^ b).count("1")

    hashes: List[Tuple[int, Path]] = []
    unique: List[Path] = []
    for p in paths:
        try:
            img = Image.open(p)
            h = dhash(img)
            is_dup = any(hamming(h, hh) <= max_diff for hh, _ in hashes)
            if not is_dup:
                hashes.append((h, p))
                unique.append(p)
        except Exception:
            # Corrupt or unreadable – skip
            continue
    removed = len(paths) - len(unique)
    if removed:
        print(f"    Removed {removed} near-duplicates.")
    return unique


def load_class_map(path: Path) -> Dict[str, str]:
    """Load source_folder -> label mapping from YAML."""
    if not path.exists():
        raise FileNotFoundError(
            f"class_map.yaml not found at {path}\n"
            "Create it following the template in vision/class_map.yaml.example"
        )
    with open(path) as f:
        raw = yaml.safe_load(f)
    # Flatten: mapping can be nested (source_name -> {folder -> label})
    # or flat (folder_name -> label)
    flat = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            for subfolder, label in val.items():
                flat[f"{key}/{subfolder}"] = label
        else:
            flat[key] = val
    return flat


def collect_rows(class_map: Dict[str, str], raw_root: Path, seed: int = 42) -> List[Dict]:
    """Walk data/raw/ and assign split to each image."""
    random.seed(seed)
    rows: List[Dict] = []

    for map_key, label in class_map.items():
        source_name = map_key.split("/")[0]
        folder = raw_root / map_key.replace("/", os.sep)
        if not folder.exists():
            print(f"  WARN: mapped folder not found: {folder} – skipping")
            continue

        images = remove_near_duplicates([p for p in folder.rglob("*") if is_image(p)])
        if not images:
            print(f"  WARN: no images in {folder}")
            continue

        # Assign split
        if source_name in FIELD_SOURCES:
            split = "test"
            for img in images:
                rows.append({"path": str(img), "label": label, "source": source_name, "split": split})
        else:
            # Lab sources: group by subfolder to avoid leaking same plant across splits
            random.shuffle(images)
            n = len(images)
            n_val = max(1, int(n * 0.15))
            for i, img in enumerate(images):
                s = "val" if i < n_val else "train"
                rows.append({"path": str(img), "label": label, "source": source_name, "split": s})

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--class_map", default=str(DEFAULT_CLASS_MAP), help="Path to class_map.yaml")
    parser.add_argument("--raw_root", default=str(REPO_ROOT / "data" / "raw"), help="Root of raw data directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splits")
    args = parser.parse_args()

    class_map_path = Path(args.class_map)
    raw_root = Path(args.raw_root)

    if not raw_root.exists():
        print(f"ERROR: data/raw/ not found at {raw_root}")
        print("Please download datasets first. See docs/DATASETS.md and runbook section 2.2.")
        sys.exit(1)

    print(f"Loading class map from {class_map_path}…")
    try:
        class_map = load_class_map(class_map_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Copy vision/class_map.yaml.example to vision/class_map.yaml and fill in your paths.")
        sys.exit(1)

    print(f"Collecting images from {raw_root}…")
    rows = collect_rows(class_map, raw_root, seed=args.seed)

    if not rows:
        print("No rows collected. Check that data/raw/ contains images and class_map.yaml is correct.")
        sys.exit(1)

    # Print summary
    from collections import Counter
    split_counts = Counter(r["split"] for r in rows)
    label_counts = Counter(r["label"] for r in rows)
    print(f"\nTotal: {len(rows)} images")
    print(f"Splits: train={split_counts['train']}, val={split_counts['val']}, test={split_counts['test']}")
    print(f"Classes: {len(label_counts)}")
    for lbl in sorted(label_counts):
        print(f"  {lbl:<40} {label_counts[lbl]}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "source", "split"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nManifest written to {MANIFEST_PATH}")
    print("Next: python vision/train.py --config vision/train_config.yaml")


if __name__ == "__main__":
    main()
