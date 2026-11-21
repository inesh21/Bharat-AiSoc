"""Clarification loop resolver (Task B5).

Evaluates whether the top 2 vision diagnoses are close (delta < 0.15) and
returns a discriminating clarifying question, or applies farmer's answer to re-weight scores.
"""

from typing import Dict, Any, List, Optional, Tuple
import yaml


class ClarificationEngine:
    """Manages clarifying questions for ambiguous disease pairs."""

    def __init__(self, config_path: str = "knowledge/clarifications.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self.pairs = data.get("pairs", {})

    def check_ambiguity(
        self,
        predictions: List[Dict[str, Any]],
        confidence_threshold_delta: float = 0.15,
        lang: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Checks if top-2 predictions are within confidence delta and returns a clarifying question."""
        if len(predictions) < 2:
            return None

        top1 = predictions[0]
        top2 = predictions[1]

        delta = top1["confidence"] - top2["confidence"]
        if delta >= confidence_threshold_delta:
            return None

        labels = {top1["label"], top2["label"]}

        for pair_key, pair_info in self.pairs.items():
            pair_classes = set(pair_info.get("classes", []))
            if labels == pair_classes:
                questions = pair_info.get("questions", [])
                if questions:
                    q = questions[0]
                    text_dict = q.get("text", {})
                    q_text = text_dict.get(lang, text_dict.get("en", ""))
                    return {
                        "question_id": q.get("question_id"),
                        "text": q_text,
                        "options": q.get("options", ["yes", "no", "not_sure"]),
                        "pair_key": pair_key
                    }
        return None

    def apply_answer(
        self,
        pair_key: str,
        question_id: str,
        answer: str,
        predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Applies farmer's clarification answer to re-weight candidate predictions."""
        pair_info = self.pairs.get(pair_key, {})
        for q in pair_info.get("questions", []):
            if q.get("question_id") == question_id:
                adjustments = q.get("weight_adjustments", {}).get(answer, {})
                adjusted_preds = []
                for p in predictions:
                    lbl = p["label"]
                    adj = adjustments.get(lbl, 0.0)
                    new_conf = max(0.01, min(0.99, p["confidence"] + adj))
                    adjusted_preds.append({
                        "label": lbl,
                        "type": p["type"],
                        "confidence": round(new_conf, 2)
                    })
                # Re-sort descending
                adjusted_preds.sort(key=lambda x: x["confidence"], reverse=True)
                return adjusted_preds
        return predictions
