"""Dataset loading, deduplication, and field-condition augmentation (Tasks A3, A4, A7).

Includes:
- Perceptual hash deduplication (dHash / aHash via PIL / OpenCV)
- Group/Batch-aware dataset splitting
- Field condition augmentations: ColorJitter, RandomAffine, RandomErasing/Cutout, GaussianBlur
"""

import os
import glob
from typing import List, Dict, Tuple, Set, Optional
import cv2
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms as T


def compute_dhash(image_path: str, hash_size: int = 8) -> Optional[int]:
    """Computes difference hash (dHash) for duplicate / near-duplicate detection."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
            pixels = np.array(img, dtype=np.int32)
            # Compare adjacent pixels
            diff = pixels[:, 1:] > pixels[:, :-1]
            return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
    except Exception:
        return None


def deduplicate_dataset(
    image_paths: List[str],
    max_hamming_distance: int = 2,
    hash_size: int = 8,
) -> Tuple[List[str], List[str]]:
    """Identifies and filters near-duplicate images based on dHash Hamming distance.

    Returns:
        (unique_paths, duplicate_paths)
    """
    seen_hashes: Dict[int, str] = {}
    unique_paths: List[str] = []
    duplicate_paths: List[str] = []

    for path in image_paths:
        h = compute_dhash(path, hash_size=hash_size)
        if h is None:
            duplicate_paths.append(path)
            continue

        is_dup = False
        for seen_h in seen_hashes:
            # Hamming distance
            dist = bin(h ^ seen_h).count("1")
            if dist <= max_hamming_distance:
                is_dup = True
                duplicate_paths.append(path)
                break

        if not is_dup:
            seen_hashes[h] = path
            unique_paths.append(path)

    return unique_paths, duplicate_paths


def get_field_transforms(
    input_size: int = 224,
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
    std: Tuple[float, float, float] = (0.229, 0.224, 0.225),
    is_train: bool = True,
) -> T.Compose:
    """Standard transformations with aggressive field-condition augmentations for training."""
    if is_train:
        return T.Compose([
            T.RandomResizedCrop(input_size, scale=(0.7, 1.0)),
            T.RandomHorizontalFlip(p=0.5),
            T.RandomVerticalFlip(p=0.3),
            T.RandomRotation(degrees=30),
            T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
            T.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 2.0)),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
            T.RandomErasing(p=0.2, scale=(0.02, 0.2), value="random"),
        ])
    else:
        return T.Compose([
            T.Resize((input_size, input_size)),
            T.ToTensor(),
            T.Normalize(mean=mean, std=std),
        ])
