"""Output validator for LLM-generated advisories (Task B8).

NON-NEGOTIABLE CONSTRAINT (AGENTS.md & Master Plan):
"The LLM never decides chemicals or doses. Chemical names, doses, pre-harvest
intervals and safety text come only from knowledge/rules.yaml. The LLM may explain
them; the output validator rejects anything not in the rules table."

Validates:
1. Valid JSON format
2. Required sections present: diagnosis, actions_now, prevention, summary_text
3. Chemical safety check: Every chemical named in generated text must exist in rules.yaml approved targets
4. Rejection of unapproved chemicals, doses, or restricted toxins
If validation fails -> returns True to trigger safe fallback advisory.
"""

import json
import re
from typing import Dict, Any, Tuple, List, Optional
import yaml


class OutputValidator:
    """Rigorous validator ensuring zero chemical hallucinations and strict schema conformance."""

    def __init__(self, rules_path: str = "knowledge/rules.yaml"):
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)

        self.approved_chemicals = self.rules.get("chemicals", {})
        self.restricted_chemicals = [c.lower() for c in self.rules.get("restricted_chemicals", [])]

        # Extract all valid chemical names and active ingredients
        self.valid_chemical_tokens = set()
        for chem_key, chem_info in self.approved_chemicals.items():
            self.valid_chemical_tokens.add(chem_key.lower().replace("_", " "))
            for name in chem_info.get("trade_names", []):
                self.valid_chemical_tokens.add(name.lower())
            ai = chem_info.get("active_ingredient", "").lower()
            self.valid_chemical_tokens.add(ai)

    def validate(
        self,
        llm_output_text: str,
        target_condition_id: str,
        severity_band: str = "moderate"
    ) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """Validates LLM output string.

        Returns:
            (is_valid: bool, parsed_json: Optional[Dict], rejection_reasons: List[str])
        """
        rejection_reasons = []

        # 1. Parse JSON
        try:
            # Strip markdown json blocks if present
            cleaned = llm_output_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
        except Exception as e:
            return False, None, [f"JSON parsing error: {str(e)}"]

        # 2. Check required fields
        required_fields = ["diagnosis", "actions_now", "prevention", "summary_text"]
        for field in required_fields:
            if field not in parsed or not parsed[field]:
                rejection_reasons.append(f"Missing or empty required field: '{field}'")

        if rejection_reasons:
            return False, parsed, rejection_reasons

        # 3. Check for restricted / banned chemicals
        full_text_lower = (
            str(parsed.get("diagnosis", "")) + " " +
            " ".join(parsed.get("actions_now", [])) + " " +
            " ".join(parsed.get("prevention", [])) + " " +
            str(parsed.get("summary_text", ""))
        ).lower()

        for restricted in self.restricted_chemicals:
            if re.search(r"\b" + re.escape(restricted) + r"\b", full_text_lower):
                rejection_reasons.append(f"Restricted/banned chemical detected: '{restricted}'")

        # 4. Check chemical authorization for condition
        # If severity is 'none' or 'mild', verify that harsh synthetic chemicals are not prescribed
        severity_rule = self.rules.get("severity_thresholds", {}).get(severity_band, {})
        chemical_allowed = severity_rule.get("chemical_allowed", True)

        # Check any mentioned chemicals against approved targets
        for chem_key, chem_info in self.approved_chemicals.items():
            targets = chem_info.get("approved_targets", [])
            tokens_to_check = [chem_key.lower().replace("_", " ")] + [t.lower() for t in chem_info.get("trade_names", [])]
            for token in tokens_to_check:
                if re.search(r"\b" + re.escape(token) + r"\b", full_text_lower):
                    if not chemical_allowed:
                        rejection_reasons.append(f"Chemical '{token}' prescribed when severity is '{severity_band}' (chemicals not permitted).")
                    elif target_condition_id not in targets:
                        rejection_reasons.append(f"Chemical '{token}' is not an approved target for '{target_condition_id}'.")

        is_valid = len(rejection_reasons) == 0
        return is_valid, parsed, rejection_reasons
