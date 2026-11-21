"""vision/prepare_data.py – Data preparation for vision model training.

Phase 2.3 of the runbook.

Reads datasets from data/raw/<source_name>/ (or temporary directories)
and physically saves every resized, deduplicated RGB JPEG into:
    data/processed/images/<source>/<label>/
and writes that data/processed/images/... path into:
    data/processed/manifest.csv (with columns: path,label,source,split)

Features:
- Filters/processes specific source datasets or all in class_map.yaml.
- Caps samples per class PER SPLIT GROUP (train_val vs test) so test datasets are not blocked.
- Resizes lab/train_val images to max 256px and field/test images to max 512px.
- Converts everything to RGB JPEG format and saves to data/processed/images/.
- Deduplicates using perceptual hash (dHash).
- Appends to data/processed/manifest.csv without duplicate rows.
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
PROCESSED_IMAGES_DIR = REPO_ROOT / "data" / "processed" / "images"

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
            continue
    removed = len(paths) - len(unique)
    if removed:
        print(f"    Removed {removed} duplicates/near-duplicates.")
    return unique


def save_processed_image(src_path: Path, dest_path: Path, max_side: int = 256) -> bool:
    """Reads image from src_path, resizes, converts to RGB JPEG, and saves to dest_path."""
    if Image is None:
        return False
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            if max_side > 0 and max(w, h) > max_side:
                scale = max_side / float(max(w, h))
                new_size = (int(round(w * scale)), int(round(h * scale)))
                resample = getattr(Image, "Resampling", Image).LANCZOS
                img = img.resize(new_size, resample=resample)
            
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            img.save(dest_path, format="JPEG", quality=95)
        return True
    except Exception as e:
        print(f"    WARN: Failed to process & save {src_path} -> {dest_path}: {e}")
        return False


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
    split_group_counts: Dict[str, Dict[str, int]] = {
        "train_val": defaultdict(int),
        "test": defaultdict(int),
    }

    if not manifest_path.exists():
        return existing_rows, existing_paths, split_group_counts

    with open(manifest_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            existing_rows.append(r)
            p_norm = os.path.normpath(r["path"]).lower()
            existing_paths.add(p_norm)
            
            label = r["label"]
            split = r["split"]
            if split == "test":
                split_group_counts["test"][label] += 1
            else:
                split_group_counts["train_val"][label] += 1

    return existing_rows, existing_paths, split_group_counts


def collect_rows(
    class_map: Dict[str, str],
    raw_root: Path,
    processed_dir: Path,
    target_source: str = None,
    max_per_class: int = 600,
    max_side: int = 256,
    existing_paths: Set[str] = None,
    existing_split_group_counts: Dict[str, Dict[str, int]] = None,
    seed: int = 42
) -> List[Dict[str, str]]:
    """Walk data/raw/ and save processed images to data/processed/images/."""
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

            random.shuffle(fresh_imgs)
            unique_imgs = remove_near_duplicates(fresh_imgs[: min(len(fresh_imgs), quota_remaining + 200)])
            selected = unique_imgs[:quota_remaining]

            if not selected:
                continue

            # Assign split and physically save to processed directory
            target_label_dir = processed_dir / source_name / label
            target_label_dir.mkdir(parents=True, exist_ok=True)

            if is_field:
                split = "test"
                saved_count = 0
                for img in selected:
                    dest_fname = f"{img.stem}_{hashlib.md5(str(img).encode()).hexdigest()[:6]}.jpg"
                    dest_path = target_label_dir / dest_fname
                    if save_processed_image(img, dest_path, max_side=max_side):
                        new_rows.append({"path": str(dest_path), "label": label, "source": source_name, "split": split})
                        existing_paths.add(os.path.normpath(str(dest_path)).lower())
                        saved_count += 1
                current_test[label] += saved_count
            else:
                n = len(selected)
                n_val = max(1, int(n * 0.15)) if n >= 5 else 0
                saved_count = 0
                for i, img in enumerate(selected):
                    s = "val" if i < n_val else "train"
                    dest_fname = f"{img.stem}_{hashlib.md5(str(img).encode()).hexdigest()[:6]}.jpg"
                    dest_path = target_label_dir / dest_fname
                    if save_processed_image(img, dest_path, max_side=max_side):
                        new_rows.append({"path": str(dest_path), "label": label, "source": source_name, "split": s})
                        existing_paths.add(os.path.normpath(str(dest_path)).lower())
                        saved_count += 1
                current_train_val[label] += saved_count

    return new_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare vision training dataset and manifest.")
    parser.add_argument("--class_map", default=str(DEFAULT_CLASS_MAP), help="Path to class_map.yaml")
    parser.add_argument("--raw_root", default=str(REPO_ROOT / "data" / "raw"), help="Root of raw data directory")
    parser.add_argument("--processed_dir", default=str(PROCESSED_IMAGES_DIR), help="Root directory for saved processed images")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Path to manifest.csv")
    parser.add_argument("--source", default=None, help="Specific source folder to process (e.g., plantvillage)")
    parser.add_argument("--max-per-class", type=int, default=600, help="Max images per class per split group (default 600)")
    parser.add_argument("--max-side", type=int, default=256, help="Max dimension in pixels for images (default 256)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    class_map_path = Path(args.class_map)
    raw_root = Path(args.raw_root)
    processed_dir = Path(args.processed_dir)
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
        processed_dir=processed_dir,
        target_source=args.source,
        max_per_class=args.max_per_class,
        max_side=args.max_side,
        existing_paths=existing_paths,
        existing_split_group_counts=existing_split_counts,
        seed=args.seed,
    )

    if not new_rows:
        print("No new images to add to manifest.")
        return

    # Append new rows to manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = manifest_path.exists() and manifest_path.stat().st_size > 0
    with open(manifest_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "source", "split"])
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    all_rows = existing_rows + new_rows
    print(f"\nSuccessfully added {len(new_rows)} images to {manifest_path} (Total now: {len(all_rows)}).")

    # Summary
    split_counts: Dict[str, int] = defaultdict(int)
    class_counts: Dict[str, int] = defaultdict(int)
    for r in all_rows:
        split_counts[r["split"]] += 1
        class_counts[r["label"]] += 1

    print("Overall Splits: " + ", ".join(f"{s}={c}" for s, c in sorted(split_counts.items())))
    print(f"Class counts ({len(class_counts)} classes):")
    for l, c in sorted(class_counts.items()):
        print(f"  {l:<38} {c:>5}")


if __name__ == "__main__":
    main()
