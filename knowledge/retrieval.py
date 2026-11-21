"""Knowledge Base loader and deterministic retrieval engine (Task B4).

Performs:
1. Exact indexed lookup by class identifier (crop__condition)
2. Severity-appropriate treatment filtering
3. Safe template-based advisory construction (used directly or as fallback)
"""

import json
import os
from typing import Dict, Any, List, Optional
import yaml


class KnowledgeBase:
    """Manages curated agronomy entries and safety rules."""

    def __init__(self, kb_path: str = "knowledge/kb.json", rules_path: str = "knowledge/rules.yaml"):
        with open(kb_path, "r", encoding="utf-8") as f:
            raw_entries = json.load(f)
            self.entries: Dict[str, Dict[str, Any]] = {e["id"]: e for e in raw_entries}

        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules: Dict[str, Any] = yaml.safe_load(f)

    def get_entry(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves exact knowledge entry by class ID."""
        return self.entries.get(condition_id)

    def get_approved_chemicals_for_target(self, target_id: str) -> List[Dict[str, Any]]:
        """Returns verified chemical options strictly from rules.yaml."""
        chemicals = self.rules.get("chemicals", {})
        approved = []
        for chem_key, chem_data in chemicals.items():
            if target_id in chem_data.get("approved_targets", []):
                approved.append({
                    "id": chem_key,
                    "active_ingredient": chem_data.get("active_ingredient"),
                    "dose": chem_data.get("dose"),
                    "phi_days": chem_data.get("phi_days"),
                    "safety": chem_data.get("safety")
                })
        return approved

    def build_fallback_advisory(self, condition_id: str, severity_band: str = "moderate", lang: str = "en") -> Dict[str, Any]:
        """Constructs a deterministic, 100% verified advisory template directly from the knowledge base."""
        entry = self.get_entry(condition_id)
        if not entry or condition_id == "unknown":
            return {
                "schema_version": "1.0",
                "status": "final",
                "clarification": null_or_none(),
                "diagnosis": "Condition Unknown or Inconclusive",
                "severity_band": severity_band,
                "actions_now": [
                    "Do not apply unverified chemical sprays.",
                    "Collect a fresh physical leaf sample in a clean paper bag.",
                    "Consult your nearest Krishi Vigyan Kendra (KVK) or State Agricultural Department officer."
                ],
                "prevention": [
                    "Inspect surrounding plants and maintain general field sanitation."
                ],
                "seek_help": True,
                "source_ids": ["kb:unknown"],
                "used_fallback": True,
                "language": lang,
                "text": "The condition could not be conclusively identified. Please consult your local agricultural extension officer."
            }

        actions_by_sev = entry.get("severity_actions", {})
        band_actions = actions_by_sev.get(severity_band, actions_by_sev.get("moderate", []))

        # Check severity threshold rule
        severity_rule = self.rules.get("severity_thresholds", {}).get(severity_band, {})
        chemical_allowed = severity_rule.get("chemical_allowed", True)

        actions_now = list(band_actions)
        if not chemical_allowed:
            # Filter out any chemical mentions if mild or none
            actions_now = [a for a in actions_now if not ("WP" in a or "EC" in a or "fungicide" in a.lower())]

        prevention = entry.get("prevention", [])
        crop_name = entry.get("crop", "crop").capitalize()
        condition_name = entry.get("id", "").replace("__", " - ").replace("_", " ").title()

        full_text = f"Diagnosis: {condition_name}. Severity: {severity_band.capitalize()}. Immediate action: {actions_now[0] if actions_now else 'Scout fields.'}"

        return {
            "schema_version": "1.0",
            "status": "final",
            "clarification": None,
            "diagnosis": condition_name,
            "severity_band": severity_band,
            "actions_now": actions_now,
            "prevention": prevention,
            "seek_help": condition_id == "unknown",
            "source_ids": [f"kb:{condition_id}"],
            "used_fallback": True,
            "language": lang,
            "text": full_text
        }


def null_or_none():
    return None
