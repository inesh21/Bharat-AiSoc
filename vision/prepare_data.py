"""vision/prepare_data.py – Data preparation for vision model training.

Phase 2.3 of the runbook.

Reads datasets from data/raw/<source_name>/ and writes/appends to
data/processed/manifest.csv with columns: path,label,source,split

Features:
- Filters/processes specific source datasets or all in class_map.yaml.
- Caps samples per class PER SPLIT GROUP (train_val vs test) so test datasets are not blocked.
- Resizes lab images so max dimension does not exceed --max-side (default: 256px),
  saving in-place or into processed location.
- Deduplicates using perceptual hash (dHash).
- Appends to data/processed/manifest.csv without overwriting existing records.
"""

import argparse
import csv
import hashlib
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    import yaml
except ImportError:
    raise ImportError("Install pyyaml: pip install pyyaml")

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

DEFAULT_CLASS_MAP = REPO_ROOT / "vision" / "class_map.yaml"
MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "manifest.csv"

# Sources that are always assigned to test (field-style images)
FIELD_SOURCES = {
    "own_field",
    "plantdoc",
    "riceleafbd",
    "sar_cld_2024",
    "field_maize_8",
    "unknown_test",
}

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in VALID_IMAGE_EXTS


def compute_dhash(img: Image.Image, size: int = 8) -> int:
    """Computes difference hash (dHash) for near-duplicate detection."""
    resample = getattr(Image, "Resampling", Image).BILINEAR
    gray = img.convert("L").resize((size + 1, size), resample)
    try:
        import numpy as np
        pixels = np.array(gray, dtype=np.int32)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    except ImportError:
        pixels = list(gray.getdata())
        diff = []
        for row in range(size):
            for col in range(size):
                diff.append(pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1])
        return int("".join("1" if b else "0" for b in diff), 2)


def remove_near_duplicates(
    paths: List[Path],
    hash_size: int = 8,
    max_diff: int = 2
) -> List[Path]:
    """Deduplicates using perceptual hash (dHash)."""
    if Image is None:
        print("  WARNING: Pillow not installed; skipping near-duplicate removal.")
        return paths

    def hamming(a: int, b: int) -> int:
        return bin(a ^ b).count("1")

    hashes: List[Tuple[int, Path]] = []
    unique: List[Path] = []
    for p in paths:
        try:
            with Image.open(p) as img:
                h = compute_dhash(img, size=hash_size)
            is_dup = any(hamming(h, hh) <= max_diff for hh, _ in hashes)
            if not is_dup:
                hashes.append((h, p))
                unique.append(p)
        except Exception:
            # Corrupt or unreadable – skip
            continue
    removed = len(paths) - len(unique)
    if removed:
        print(f"    Removed {removed} duplicates/near-duplicates.")
    return unique


def resize_image_if_needed(image_path: Path, max_side: int = 256) -> None:
    """Downscales image so max(width, height) <= max_side preserving aspect ratio."""
    if Image is None:
        return
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            if max(w, h) <= max_side:
                return
            img = ImageOps.exif_transpose(img)
            scale = max_side / float(max(w, h))
            new_size = (int(round(w * scale)), int(round(h * scale)))
            resample = getattr(Image, "Resampling", Image).LANCZOS
            resized = img.resize(new_size, resample=resample)
            img_format = img.format or ("JPEG" if image_path.suffix.lower() in [".jpg", ".jpeg"] else "PNG")
            if img_format == "JPEG" and resized.mode in ("RGBA", "P"):
                resized = resized.convert("RGB")
        
        resized.save(image_path, format=img_format, quality=95)
    except Exception as e:
        print(f"    WARN: Failed to resize {image_path}: {e}")


def load_class_map(path: Path) -> Dict[str, str]:
    """Load source_folder -> label mapping from YAML."""
    if not path.exists():
        raise FileNotFoundError(
            f"class_map.yaml not found at {path}\n"
            "Create it following the template in vision/class_map.yaml"
        )
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    flat = {}
    for key, val in raw.items():
        if isinstance(val, dict):
            for subfolder, label in val.items():
                flat[f"{key}/{subfolder}"] = label
        else:
            flat[key] = val
    return flat


def load_existing_manifest(manifest_path: Path) -> Tuple[List[Dict[str, str]], Set[str], Dict[str, Dict[str, int]]]:
    """Loads existing manifest rows, set of canonical paths, and counts per label per split group ('train_val' vs 'test')."""
    existing_rows: List[Dict[str, str]] = []
    existing_paths: Set[str] = set()
    # counts[split_group][label]
    split_group_counts: Dict[str, Dict[str, int]] = {
        "train_val": defaultdict(int),
        "test": defaultdict(int),
    }

    if manifest_path.exists() and manifest_path.stat().st_size > 0:
        with open(manifest_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                existing_rows.append(r)
                existing_paths.add(os.path.normpath(r["path"]).lower())
                grp = "test" if r["split"] == "test" else "train_val"
                split_group_counts[grp][r["label"]] += 1

    return existing_rows, existing_paths, split_group_counts


def collect_rows(
    class_map: Dict[str, str],
    raw_root: Path,
    target_source: str = None,
    max_per_class: int = 600,
    max_side: int = 256,
    existing_paths: Set[str] = None,
    existing_split_group_counts: Dict[str, Dict[str, int]] = None,
    seed: int = 42
) -> List[Dict[str, str]]:
    """Walk data/raw/ and assign split to images."""
    random.seed(seed)
    if existing_paths is None:
        existing_paths = set()
    if existing_split_group_counts is None:
        existing_split_group_counts = {
            "train_val": defaultdict(int),
            "test": defaultdict(int),
        }

    current_train_val = defaultdict(int, existing_split_group_counts["train_val"])
    current_test = defaultdict(int, existing_split_group_counts["test"])
    new_rows: List[Dict[str, str]] = []

    # Group class_map items by label
    items_by_label: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for map_key, label in class_map.items():
        source_name = map_key.split("/")[0]
        if target_source and source_name != target_source:
            continue
        items_by_label[label].append((map_key, source_name))

    print(f"Target source filter: {target_source or 'ALL'}")
    print(f"Max samples per class limit (per split group): {max_per_class}")
    print(f"Max image side: {max_side}px")

    for label, items in items_by_label.items():
        for map_key, source_name in items:
            is_field = source_name in FIELD_SOURCES
            split_group = "test" if is_field else "train_val"
            already_have = current_test[label] if is_field else current_train_val[label]
            quota_remaining = max_per_class - already_have

            if quota_remaining <= 0:
                print(f"  [{source_name}] Class '{label}' already has {already_have} >= {max_per_class} for {split_group}. Skipping.")
                continue

            folder = raw_root / map_key.replace("/", os.sep)
            if not folder.exists():
                continue

            all_imgs = [p for p in folder.rglob("*") if is_image(p)]
            fresh_imgs = [p for p in all_imgs if os.path.normpath(str(p)).lower() not in existing_paths]
            if not fresh_imgs:
                continue

            print(f"Processing '{map_key}' -> label '{label}' ({already_have} existing in {split_group}, {len(fresh_imgs)} fresh, quota: {quota_remaining})")

            # Shuffle for representative random sampling
            random.shuffle(fresh_imgs)

            # Deduplicate up to needed quota
            unique_imgs = remove_near_duplicates(fresh_imgs[: min(len(fresh_imgs), quota_remaining + 200)])
            selected = unique_imgs[:quota_remaining]

            if not selected:
                continue

            # Resize images if needed
            if max_side > 0:
                for img_p in selected:
                    resize_image_if_needed(img_p, max_side=max_side)

            # Assign split
            if is_field:
                split = "test"
                for img in selected:
                    new_rows.append({"path": str(img), "label": label, "source": source_name, "split": split})
                current_test[label] += len(selected)
            else:
                n = len(selected)
                n_val = max(1, int(n * 0.15)) if n >= 5 else 0
                for i, img in enumerate(selected):
                    s = "val" if i < n_val else "train"
                    new_rows.append({"path": str(img), "label": label, "source": source_name, "split": s})
                current_train_val[label] += len(selected)

    return new_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare vision training dataset and manifest.")
    parser.add_argument("--class_map", default=str(DEFAULT_CLASS_MAP), help="Path to class_map.yaml")
    parser.add_argument("--raw_root", default=str(REPO_ROOT / "data" / "raw"), help="Root of raw data directory")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Path to manifest.csv")
    parser.add_argument("--source", default=None, help="Specific source folder to process (e.g., plantvillage)")
    parser.add_argument("--max-per-class", type=int, default=600, help="Max images per class per split group (default 600)")
    parser.add_argument("--max-side", type=int, default=256, help="Max dimension in pixels for lab images (default 256)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    class_map_path = Path(args.class_map)
    raw_root = Path(args.raw_root)
    manifest_path = Path(args.manifest)

    if not raw_root.exists():
        print(f"ERROR: data/raw/ not found at {raw_root}")
        sys.exit(1)

    print(f"Loading class map from {class_map_path}…")
    try:
        class_map = load_class_map(class_map_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    existing_rows, existing_paths, existing_split_counts = load_existing_manifest(manifest_path)
    if existing_rows:
        print(f"Found existing manifest at {manifest_path} with {len(existing_rows)} entries.")
    else:
        print(f"No existing manifest entries found at {manifest_path}. Will create new manifest.")

    new_rows = collect_rows(
        class_map=class_map,
        raw_root=raw_root,
        target_source=args.source,
        max_per_class=args.max_per_class,
        max_side=args.max_side,
        existing_paths=existing_paths,
        existing_split_group_counts=existing_split_counts,
        seed=args.seed
    )

    if not new_rows:
        print("No new images to add to manifest.")
        return

    # Combine existing + new rows
    combined_rows = existing_rows + new_rows

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "source", "split"])
        writer.writeheader()
        writer.writerows(combined_rows)

    print(f"\nSuccessfully added {len(new_rows)} images to {manifest_path} (Total now: {len(combined_rows)}).")

    # Print summary breakdown
    from collections import Counter
    split_counts = Counter(r["split"] for r in combined_rows)
    label_counts = Counter(r["label"] for r in combined_rows)
    print(f"Overall Splits: train={split_counts['train']}, val={split_counts['val']}, test={split_counts['test']}")
    print(f"Class counts ({len(label_counts)} classes):")
    for lbl in sorted(label_counts):
        print(f"  {lbl:<38} {label_counts[lbl]}")


if __name__ == "__main__":
    main()
