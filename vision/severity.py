"""Severity estimation module based on lesion area percentage (Task A11).

Method:
1. Segment the leaf body from background using color spaces (HSV + Otsu/thresholding).
2. Segment diseased lesions (necrotic spots, chlorosis, blights, rust pustules) within leaf mask.
3. Compute lesion percentage: (lesion_pixels / leaf_pixels) * 100.
4. Map percentage to agronomic severity bands:
   - 'none': 0% (healthy)
   - 'mild': 0% < area <= 10%
   - 'moderate': 10% < area <= 30%
   - 'severe': area > 30%
"""

from typing import Dict, Tuple, Optional
import cv2
import numpy as np


class SeverityEstimator:
    """Estimates leaf lesion percentage and maps to categorical severity bands."""

    DEFAULT_BANDS = {
        "none": (0.0, 0.0),
        "mild": (0.0, 10.0),
        "moderate": (10.0, 30.0),
        "severe": (30.0, 100.0),
    }

    def __init__(self, bands: Optional[Dict[str, Tuple[float, float]]] = None):
        self.bands = bands or self.DEFAULT_BANDS

    def segment_leaf(self, bgr: np.ndarray) -> np.ndarray:
        """Extracts binary mask of the leaf against background."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        
        # Plant vegetation HSV range: covers healthy green, pale yellow, and blight brown
        lower_leaf = np.array([5, 20, 20], dtype=np.uint8)
        upper_leaf = np.array([95, 255, 255], dtype=np.uint8)
        leaf_mask = cv2.inRange(hsv, lower_leaf, upper_leaf)

        # Morphological clean-up: close holes inside leaf, remove background noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        leaf_mask = cv2.morphologyEx(leaf_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        return leaf_mask

    def segment_lesions(self, bgr: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
        """Extracts lesions (spots, blight, necroses) strictly confined to the leaf mask."""
        if cv2.countNonZero(leaf_mask) == 0:
            return np.zeros_like(leaf_mask)

        # In HSV, dark brown/black necrotic tissue has low value/saturation or brown hue
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Necrotic/dark spots: low brightness inside leaf or dark brown
        necrotic = ((v < 100) | ((h <= 18) & (s >= 30))) & (leaf_mask > 0)
        
        # Chlorotic/yellow/rust spots: Hue < 28 or Hue > 85 inside leaf with moderate-to-high saturation
        chlorotic = ((h < 28) | (h > 88)) & (s > 50) & (leaf_mask > 0)

        lesion_mask = np.zeros(leaf_mask.shape, dtype=np.uint8)
        lesion_mask[necrotic | chlorotic] = 255

        # Morphological smoothing to suppress isolated noisy pixels
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        lesion_mask = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel)

        return lesion_mask

    def map_to_band(self, percent: float) -> str:
        """Categorizes lesion percentage into standard severity bands."""
        if percent <= 0.05:
            return "none"
        elif percent <= 10.0:
            return "mild"
        elif percent <= 30.0:
            return "moderate"
        else:
            return "severe"

    def estimate(self, image_input, is_healthy: bool = False) -> Dict:
        """Estimates lesion percentage and severity band.

        Returns:
            Dict conforming to Contract 1:
            {
                "percent": float (0.0 to 100.0),
                "band": "none" | "mild" | "moderate" | "severe"
            }
        """
        if is_healthy:
            return {"percent": 0.0, "band": "none"}

        if isinstance(image_input, str):
            bgr = cv2.imread(image_input)
            if bgr is None:
                return {"percent": 0.0, "band": "none"}
        elif isinstance(image_input, np.ndarray):
            bgr = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        leaf_mask = self.segment_leaf(bgr)
        leaf_pixels = cv2.countNonZero(leaf_mask)

        if leaf_pixels == 0:
            return {"percent": 0.0, "band": "none"}

        lesion_mask = self.segment_lesions(bgr, leaf_mask)
        lesion_pixels = cv2.countNonZero(lesion_mask)

        lesion_ratio = lesion_pixels / float(leaf_pixels)
        percent = float(min(100.0, round(lesion_ratio * 100.0, 1)))
        band = self.map_to_band(percent)

        return {
            "percent": percent,
            "band": band
        }
