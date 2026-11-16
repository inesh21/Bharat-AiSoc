"""Image quality assessment module for leaf photographs (Task A10).

Checks for:
1. Blur (variance of Laplacian)
2. Brightness (mean pixel luminance in Grayscale/V-channel)
3. Leaf presence (green/yellow vegetation mask ratio in HSV color space)

Outputs structured dictionary compatible with Contract 1 (vision result).
"""

from typing import Dict, List, Tuple
import cv2
import numpy as np


class ImageQualityChecker:
    """Evaluates whether an input photo meets quality standards for model inference."""

    def __init__(
        self,
        blur_threshold: float = 100.0,
        dark_threshold: float = 40.0,
        bright_threshold: float = 220.0,
        min_leaf_area_ratio: float = 0.05,
    ):
        self.blur_threshold = blur_threshold
        self.dark_threshold = dark_threshold
        self.bright_threshold = bright_threshold
        self.min_leaf_area_ratio = min_leaf_area_ratio

    def check_blur(self, gray: np.ndarray) -> Tuple[bool, float]:
        """Variance of Laplacian focus measure. Lower values indicate blurry images."""
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        is_blurry = laplacian_var < self.blur_threshold
        return is_blurry, laplacian_var

    def check_brightness(self, gray: np.ndarray) -> Tuple[bool, bool, float]:
        """Calculates average brightness. Identifies too_dark or too_bright conditions."""
        mean_brightness = float(np.mean(gray))
        is_too_dark = mean_brightness < self.dark_threshold
        is_too_bright = mean_brightness > self.bright_threshold
        return is_too_dark, is_too_bright, mean_brightness

    def check_leaf_presence(self, bgr: np.ndarray) -> Tuple[bool, float]:
        """Estimates vegetation/leaf area ratio using HSV color thresholding."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        
        # Green to yellow-brown foliage hue bounds in OpenCV (Hue: 0-179)
        # Green/foliage: H: 25 to 85, S: 30 to 255, V: 30 to 255
        lower_foliage = np.array([20, 25, 25], dtype=np.uint8)
        upper_foliage = np.array([90, 255, 255], dtype=np.uint8)
        
        # Brown / diseased leaf tissue: H: 10 to 25, S: 40 to 255, V: 30 to 200
        lower_brown = np.array([10, 40, 30], dtype=np.uint8)
        upper_brown = np.array([25, 255, 200], dtype=np.uint8)

        mask_foliage = cv2.inRange(hsv, lower_foliage, upper_foliage)
        mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
        leaf_mask = cv2.bitwise_or(mask_foliage, mask_brown)

        total_pixels = bgr.shape[0] * bgr.shape[1]
        leaf_pixels = int(cv2.countNonZero(leaf_mask))
        ratio = float(leaf_pixels / max(total_pixels, 1))

        has_leaf = ratio >= self.min_leaf_area_ratio
        return has_leaf, ratio

    def assess(self, image_input) -> Dict:
        """Assesses image quality from file path or BGR numpy array.

        Returns:
            Dict containing:
                - ok (bool): True if no issues detected
                - issues (List[str]): List of issues ('blurry', 'too_dark', 'too_bright', 'no_leaf')
                - metrics (Dict): Raw numeric metrics for telemetry/debugging
        """
        if isinstance(image_input, str):
            bgr = cv2.imread(image_input)
            if bgr is None:
                return {
                    "ok": False,
                    "issues": ["corrupt_or_unreadable"],
                    "metrics": {}
                }
        elif isinstance(image_input, np.ndarray):
            bgr = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        is_blurry, blur_val = self.check_blur(gray)
        is_too_dark, is_too_bright, brightness_val = self.check_brightness(gray)
        has_leaf, leaf_ratio = self.check_leaf_presence(bgr)

        issues: List[str] = []
        if is_blurry:
            issues.append("blurry")
        if is_too_dark:
            issues.append("too_dark")
        if is_too_bright:
            issues.append("too_bright")
        if not has_leaf:
            issues.append("no_leaf")

        return {
            "ok": len(issues) == 0,
            "issues": issues,
            "metrics": {
                "blur_laplacian_var": round(blur_val, 2),
                "brightness_mean": round(brightness_val, 2),
                "leaf_area_ratio": round(leaf_ratio, 4),
            }
        }
