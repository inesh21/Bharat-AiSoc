import pytest
import json
import yaml

from knowledge.retrieval import KnowledgeBase
from knowledge.clarifications import ClarificationEngine
from llm.validator import OutputValidator
from llm.prompts import build_advisory_prompt, SYSTEM_PROMPT
from llm.pipeline import AdvisoryPipeline


def test_kb_schema_and_sources():
    kb = KnowledgeBase(kb_path="knowledge/kb.json", rules_path="knowledge/rules.yaml")
    # Verified labels from Track A taxonomy
    labels = [
        "tomato__healthy", "tomato__early_blight", "tomato__late_blight",
        "tomato__septoria_leaf_spot", "tomato__bacterial_spot", "potato__healthy",
        "potato__early_blight", "potato__late_blight", "rice__healthy",
        "rice__blast", "rice__brown_spot", "rice__bacterial_blight",
        "maize__healthy", "maize__common_rust", "maize__northern_leaf_blight",
        "cotton__healthy", "cotton__bacterial_blight", "pest__fall_armyworm", "unknown"
    ]

    # Every label must have a corresponding KB entry with source citation
    for lbl in labels:
        entry = kb.get_entry(lbl)
        assert entry is not None, f"Missing KB entry for {lbl}"
        assert "sources" in entry and len(entry["sources"]) > 0, f"Missing source citation for {lbl}"
        assert "severity_actions" in entry


def test_rules_yaml_structure():
    with open("knowledge/rules.yaml", "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    assert "chemicals" in rules
    assert "restricted_chemicals" in rules
    assert "severity_thresholds" in rules


def test_clarifications_ambiguity_and_weighting():
    engine = ClarificationEngine(config_path="knowledge/clarifications.yaml")
    ambiguous_preds = [
        {"label": "tomato__early_blight", "confidence": 0.52, "type": "disease"},
        {"label": "tomato__septoria_leaf_spot", "confidence": 0.48, "type": "disease"}
    ]

    ambiguity = engine.check_ambiguity(ambiguous_preds)
    assert ambiguity is not None
    assert ambiguity["question_id"] == "q_rings_vs_specks"

    # Farmer answers target_rings -> boosts early blight
    resolved_preds = engine.apply_answer(
        pair_key=ambiguity["pair_key"],
        question_id=ambiguity["question_id"],
        answer="target_rings",
        predictions=ambiguous_preds
    )
    assert resolved_preds[0]["label"] == "tomato__early_blight"
    assert resolved_preds[0]["confidence"] > 0.80


def test_validator_approved_vs_hallucinated():
    validator = OutputValidator(rules_path="knowledge/rules.yaml")

    # Valid output with approved chemical and dose
    valid_llm = """
    {
      "diagnosis": "Early Blight on Tomato",
      "actions_now": [
        "Prune diseased lower leaves.",
        "Apply Copper Oxychloride 50% WP @ 2.5 g/L water with protective gloves."
      ],
      "prevention": ["Rotate with maize.", "Mulch with straw."],
      "summary_text": "Tomato Early Blight detected. Spray Copper Oxychloride 50% WP @ 2.5 g/L water wearing gloves."
    }
    """
    is_valid, parsed, reasons = validator.validate(valid_llm, target_condition_id="tomato__early_blight", severity_band="moderate")
    assert is_valid
    assert len(reasons) == 0

    # Invalid output with hallucinated chemical
    invalid_chem_llm = """
    {
      "diagnosis": "Early Blight on Tomato",
      "actions_now": [
        "Spray MiracleGrowMagic 500g everywhere immediately."
      ],
      "prevention": ["Rotate crops."],
      "summary_text": "Spray chemical."
    }
    """
    # Or banned chemical
    banned_llm = """
    {
      "diagnosis": "Early Blight on Tomato",
      "actions_now": [
        "Apply Monocrotophos immediately."
      ],
      "prevention": ["Rotate crops."],
      "summary_text": "Spray monocrotophos."
    }
    """
    is_valid_banned, _, reasons_banned = validator.validate(banned_llm, target_condition_id="tomato__early_blight", severity_band="moderate")
    assert not is_valid_banned
    assert any("monocrotophos" in r.lower() for r in reasons_banned)


def test_advisory_pipeline_fallback():
    pipeline = AdvisoryPipeline(
        kb_path="knowledge/kb.json",
        rules_path="knowledge/rules.yaml",
        clarifications_path="knowledge/clarifications.yaml",
        llm_generate_fn=None  # Fallback directly
    )

    req = {
        "schema_version": "1.0",
        "vision": {
            "unknown": False,
            "crop": "tomato",
            "quality": {"ok": True, "issues": []},
            "predictions": [
                {"label": "tomato__early_blight", "confidence": 0.85, "type": "disease"}
            ],
            "severity": {"percent": 18.0, "band": "moderate"}
        },
        "language": "en"
    }

    resp = pipeline.advise(req)
    assert resp["schema_version"] == "1.0"
    assert resp["status"] == "final"
    assert resp["used_fallback"] is True
    assert "Early Blight" in resp["diagnosis"]
    assert len(resp["actions_now"]) > 0
    assert len(resp["prevention"]) > 0
    assert len(resp["source_ids"]) > 0
