"""knowledge/test_safety.py – Phase 3 safety gate.

Checks:
  1. Every chemical referenced in kb.json -> chemical_options exists in
     rules.yaml -> chemicals.
  2. The chemical's approved_targets includes the kb.json entry id.
  3. No restricted chemical appears in any kb.json advisory text.
  4. Every kb.json entry has at least one source citation.
  5. Every condition id in kb.json exists in labels.json.

Run with:
    python -m pytest knowledge/test_safety.py -v

This test must pass before Checkpoint 3 (I3) is declared done.
"""

import json
import os
import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

KB_PATH = REPO_ROOT / "knowledge" / "kb.json"
RULES_PATH = REPO_ROOT / "knowledge" / "rules.yaml"
LABELS_PATH = REPO_ROOT / "labels.json"


@pytest.fixture(scope="module")
def kb():
    with open(KB_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return {entry["id"]: entry for entry in raw}


@pytest.fixture(scope="module")
def rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def labels():
    with open(LABELS_PATH, encoding="utf-8") as f:
        return set(json.load(f))


@pytest.fixture(scope="module")
def approved_chemicals(rules):
    return rules.get("chemicals", {})


@pytest.fixture(scope="module")
def restricted_chemicals(rules):
    return [c.lower() for c in rules.get("restricted_chemicals", [])]


# ---------------------------------------------------------------------------
# Test 1: Every kb.json condition id is in labels.json
# ---------------------------------------------------------------------------
def test_all_kb_ids_in_labels(kb, labels):
    missing = [cid for cid in kb if cid not in labels]
    assert not missing, (
        f"KB entries not in labels.json:\n" + "\n".join(f"  {m}" for m in missing)
    )


# ---------------------------------------------------------------------------
# Test 2: Every chemical in kb.json chemical_options exists in rules.yaml
# ---------------------------------------------------------------------------
def test_kb_chemicals_in_rules(kb, approved_chemicals):
    failures = []
    for cid, entry in kb.items():
        for chem in entry.get("chemical_options", []):
            chem_name = chem.get("name", "")
            # Match by checking if any rules.yaml trade name or key appears in the name
            found = False
            for key, chem_data in approved_chemicals.items():
                trade_names = [t.lower() for t in chem_data.get("trade_names", [])]
                key_norm = key.lower().replace("_", " ")
                ai_norm = chem_data.get("active_ingredient", "").lower()
                if (key_norm in chem_name.lower() or
                        any(t in chem_name.lower() for t in trade_names) or
                        ai_norm in chem_name.lower()):
                    found = True
                    break
            if not found:
                failures.append(f"  [{cid}] chemical_option '{chem_name}' not found in rules.yaml")

    assert not failures, (
        f"KB chemicals not in rules.yaml ({len(failures)} issues):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 3: Chemical approved_targets includes the kb entry id
# ---------------------------------------------------------------------------
def test_chemical_approved_for_condition(kb, approved_chemicals):
    failures = []
    for cid, entry in kb.items():
        for chem in entry.get("chemical_options", []):
            chem_name = chem.get("name", "")
            # Find the matching rules.yaml entry
            for key, chem_data in approved_chemicals.items():
                trade_names = [t.lower() for t in chem_data.get("trade_names", [])]
                key_norm = key.lower().replace("_", " ")
                if (key_norm in chem_name.lower() or
                        any(t in chem_name.lower() for t in trade_names)):
                    targets = chem_data.get("approved_targets", [])
                    if cid not in targets:
                        failures.append(
                            f"  [{cid}] uses '{key}' but it is not in approved_targets "
                            f"(targets: {targets})"
                        )
                    break

    assert not failures, (
        f"Chemical target mismatches ({len(failures)} issues):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 4: No restricted chemical in advisory text fields of kb.json
# ---------------------------------------------------------------------------
def test_no_restricted_chemicals_in_kb(kb, restricted_chemicals):
    failures = []
    for cid, entry in kb.items():
        # Build a text blob of all advisory text in the entry
        text_parts = entry.get("symptoms", []) + entry.get("prevention", [])
        for sev_actions in entry.get("severity_actions", {}).values():
            text_parts.extend(sev_actions)
        for chem in entry.get("chemical_options", []):
            text_parts.append(chem.get("name", ""))
            text_parts.append(chem.get("safety", ""))
        full_text = " ".join(text_parts).lower()

        for restricted in restricted_chemicals:
            pattern = re.compile(r"\b" + re.escape(restricted) + r"\b")
            if pattern.search(full_text):
                failures.append(f"  [{cid}] contains restricted chemical: '{restricted}'")

    assert not failures, (
        f"Restricted chemicals in KB ({len(failures)} issues):\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 5: Every kb.json entry has at least one source
# ---------------------------------------------------------------------------
def test_all_entries_have_sources(kb):
    missing = [cid for cid, e in kb.items() if not e.get("sources")]
    assert not missing, (
        "KB entries without any source citation:\n" + "\n".join(f"  {m}" for m in missing)
    )


# ---------------------------------------------------------------------------
# Test 6: Severity-action structure present for each condition
# ---------------------------------------------------------------------------
def test_severity_actions_present(kb):
    # Healthy and unknown conditions have no disease treatment actions – exempt them
    EXEMPTED_SUFFIXES = ("__healthy", "unknown")
    missing = []
    for cid, entry in kb.items():
        if any(cid.endswith(s) or cid == s for s in EXEMPTED_SUFFIXES):
            continue
        sa = entry.get("severity_actions", {})
        if not sa:
            missing.append(f"  [{cid}] missing severity_actions")
        elif "moderate" not in sa:
            missing.append(f"  [{cid}] severity_actions missing 'moderate' key")

    assert not missing, (
        f"Severity action issues ({len(missing)}):\n" + "\n".join(missing)
    )


# ---------------------------------------------------------------------------
# Test 7: Organic options preferred (each entry should have at least one)
# ---------------------------------------------------------------------------
def test_organic_options_present(kb):
    """Warn (not fail) if any KB entry has no organic options.

    Per AGENTS.md §12: treatment must prefer organic/IPM first steps.
    If an entry truly has none, document it explicitly in REVIEW.md.
    """
    missing = [cid for cid, e in kb.items() if not e.get("organic_options") and cid != "unknown"]
    if missing:
        import warnings
        warnings.warn(
            f"KB entries without organic_options (should document in REVIEW.md):\n" +
            "\n".join(f"  {m}" for m in missing),
            UserWarning
        )
