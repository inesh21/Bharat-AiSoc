"""Phase 4.4 – Generate parity test vectors for the advisory pipeline.

Writes test_vectors/llm/parity.json with 30+ cases covering:
  - Full advisory (fallback mode, no LLM)
  - Clarification trigger
  - Unknown / bad quality early exit
  - Validator: missing section rejection
  - Validator: restricted chemical rejection
  - Validator: chemical not approved for condition

Each case contains:
  - input:    Contract 2 request dict
  - expected: Contract 3 response (from Python pipeline in fallback mode)
  - prompt_check: expected prompt snippets that must appear if LLM is called
  - validator_cases: list of {llm_output, expected_valid, expected_reasons}
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from knowledge.retrieval import KnowledgeBase
from knowledge.clarifications import ClarificationEngine
from llm.prompts import build_advisory_prompt, SYSTEM_PROMPT
from llm.pipeline import AdvisoryPipeline
from llm.validator import OutputValidator

OUT_PATH = os.path.join(REPO_ROOT, "test_vectors", "llm", "parity.json")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

kb = KnowledgeBase(
    kb_path=os.path.join(REPO_ROOT, "knowledge", "kb.json"),
    rules_path=os.path.join(REPO_ROOT, "knowledge", "rules.yaml"),
)
clarification_engine = ClarificationEngine(
    config_path=os.path.join(REPO_ROOT, "knowledge", "clarifications.yaml")
)
pipeline = AdvisoryPipeline(
    kb_path=os.path.join(REPO_ROOT, "knowledge", "kb.json"),
    rules_path=os.path.join(REPO_ROOT, "knowledge", "rules.yaml"),
    clarifications_path=os.path.join(REPO_ROOT, "knowledge", "clarifications.yaml"),
    llm_generate_fn=None,  # Always fallback for parity generation
)
validator = OutputValidator(rules_path=os.path.join(REPO_ROOT, "knowledge", "rules.yaml"))


def make_vision(label: str, conf2: float = 0.05, conf3: float = 0.02,
                quality_ok: bool = True, unknown: bool = False,
                severity_band: str = "moderate", severity_pct: float = 18.0,
                second_label: str = None) -> dict:
    parts = label.split("__")
    crop = parts[0] if len(parts) > 1 else "unknown"
    ptype = "healthy" if label.endswith("__healthy") else ("pest" if label.startswith("pest__") else "disease")

    second = second_label or (label + "_v2")  # placeholder; callers override
    preds = [
        {"label": label, "type": ptype, "confidence": round(1.0 - conf2 - conf3, 2)},
        {"label": second, "type": "disease", "confidence": conf2},
        {"label": crop + "__healthy", "type": "healthy", "confidence": conf3},
    ]
    return {
        "schema_version": "1.0",
        "image_id": "test-uuid-" + label.replace("_", "-"),
        "model_version": "vision_v1",
        "quality": {"ok": quality_ok, "issues": []},
        "unknown": unknown,
        "crop": crop,
        "predictions": preds,
        "severity": {"percent": severity_pct, "band": severity_band},
    }


def req(label: str, lang: str = "en", answers: list = None, **kw) -> dict:
    return {
        "schema_version": "1.0",
        "vision": make_vision(label, **kw),
        "region": "in_pan_india",
        "language": lang,
        "growth_stage": "vegetative",
        "answers": answers or [],
    }


cases = []

# ------------------------------------------------------------------
# Group 1: Straightforward fallback cases (10 conditions)
# ------------------------------------------------------------------
conditions = [
    ("tomato__early_blight", "moderate"),
    ("tomato__late_blight", "severe"),
    ("tomato__septoria_leaf_spot", "mild"),
    ("tomato__bacterial_spot", "moderate"),
    ("potato__early_blight", "mild"),
    ("potato__late_blight", "severe"),
    ("rice__blast", "moderate"),
    ("rice__brown_spot", "moderate"),
    ("rice__bacterial_blight", "severe"),
    ("maize__common_rust", "moderate"),
]
for cid, band in conditions:
    r = req(cid, severity_band=band, conf2=0.05)
    r["vision"]["predictions"][1]["label"] = "unknown"
    expected = pipeline.advise(r)
    # Also build the expected prompt snippet
    entry = kb.get_entry(cid)
    kbentry_sym = entry.get("symptoms", [""])[0] if entry else ""
    cases.append({
        "id": f"fallback_{cid}_{band}",
        "description": f"Fallback advisory for {cid} at {band} severity",
        "input": r,
        "expected": expected,
        "prompt_check": {
            "must_contain": [cid.split("__")[0].capitalize(), band],
        },
        "validator_cases": [],
    })

# ------------------------------------------------------------------
# Group 2: Clarification cases (3 pairs)
# ------------------------------------------------------------------
clarification_pairs = [
    ("tomato__early_blight", "tomato__septoria_leaf_spot", "q_rings_vs_specks", "target_rings"),
    ("tomato__early_blight", "tomato__bacterial_spot", "q_concentric_vs_angular", "small_angular"),
    ("potato__early_blight", "potato__late_blight", None, None),
]
for lab1, lab2, q_id, answer in clarification_pairs:
    # Ambiguous (without answer)
    r_ambig = req(lab1, conf2=0.05)
    r_ambig["vision"]["predictions"][0]["confidence"] = 0.52
    r_ambig["vision"]["predictions"][1] = {"label": lab2, "type": "disease", "confidence": 0.47}
    expected_ambig = pipeline.advise(r_ambig)

    cases.append({
        "id": f"clarification_{lab1}_vs_{lab2}",
        "description": f"Ambiguity trigger for {lab1} vs {lab2}",
        "input": r_ambig,
        "expected": expected_ambig,
        "prompt_check": {"must_contain": []},
        "validator_cases": [],
    })

    # With answer (if pair configured)
    if q_id and answer:
        r_answered = req(lab1, conf2=0.05, answers=[{"question_id": q_id, "answer": answer}])
        r_answered["vision"]["predictions"][0]["confidence"] = 0.52
        r_answered["vision"]["predictions"][1] = {"label": lab2, "type": "disease", "confidence": 0.47}
        expected_answered = pipeline.advise(r_answered)
        cases.append({
            "id": f"clarification_answered_{lab1}_vs_{lab2}_{answer}",
            "description": f"After answer '{answer}' for {lab1} vs {lab2}",
            "input": r_answered,
            "expected": expected_answered,
            "prompt_check": {"must_contain": []},
            "validator_cases": [],
        })

# ------------------------------------------------------------------
# Group 3: Early exit (bad quality, unknown)
# ------------------------------------------------------------------
r_bad = req("tomato__early_blight", quality_ok=False)
r_bad["vision"]["quality"]["issues"] = ["blurry"]
cases.append({
    "id": "early_exit_bad_quality",
    "description": "Bad quality image → early exit with unknown fallback",
    "input": r_bad,
    "expected": pipeline.advise(r_bad),
    "prompt_check": {"must_contain": []},
    "validator_cases": [],
})

r_unk = req("unknown")
r_unk["vision"]["unknown"] = True
cases.append({
    "id": "early_exit_unknown",
    "description": "Unknown flag set → early exit with seek_help advisory",
    "input": r_unk,
    "expected": pipeline.advise(r_unk),
    "prompt_check": {"must_contain": []},
    "validator_cases": [],
})

# ------------------------------------------------------------------
# Group 4: Validator cases (bad LLM outputs)
# ------------------------------------------------------------------
def vcase(llm_text: str, condition_id: str, severity_band: str, expected_valid: bool, reason_contains: str):
    is_valid, parsed, reasons = validator.validate(llm_text, condition_id, severity_band)
    return {
        "llm_output": llm_text,
        "condition_id": condition_id,
        "severity_band": severity_band,
        "expected_valid": expected_valid,
        "expected_reason_contains": reason_contains,
        "actual_valid": is_valid,
        "actual_reasons": reasons,
    }

validator_only_cases = [
    # Good output
    vcase(
        json.dumps({
            "diagnosis": "Tomato Early Blight",
            "actions_now": ["Remove infected lower leaves and dispose off-field."],
            "prevention": ["Avoid overhead irrigation."],
            "summary_text": "Your tomato crop has early blight. Remove diseased leaves.",
        }),
        "tomato__early_blight", "moderate", True, ""
    ),
    # Missing required section
    vcase(
        json.dumps({
            "diagnosis": "Tomato Early Blight",
            "actions_now": ["Remove infected leaves."],
            "summary_text": "Some text.",
        }),
        "tomato__early_blight", "moderate", False, "prevention"
    ),
    # Restricted chemical
    vcase(
        json.dumps({
            "diagnosis": "Late Blight",
            "actions_now": ["Apply endosulfan spray."],
            "prevention": ["Scout fields."],
            "summary_text": "Use endosulfan for late blight.",
        }),
        "potato__late_blight", "severe", False, "endosulfan"
    ),
    # Chemical not approved for condition
    vcase(
        json.dumps({
            "diagnosis": "Rice Brown Spot",
            "actions_now": ["Apply Blitox copper oxychloride spray."],
            "prevention": ["Scout fields."],
            "summary_text": "Use copper oxychloride.",
        }),
        "rice__brown_spot", "moderate", False, "rice__brown_spot"
    ),
    # Chemical prescribed when mild (not allowed)
    vcase(
        json.dumps({
            "diagnosis": "Tomato Early Blight (mild)",
            "actions_now": ["Spray chlorothalonil at 2g/L."],
            "prevention": ["Rotate crops."],
            "summary_text": "Use chlorothalonil for mild early blight.",
        }),
        "tomato__early_blight", "mild", False, "mild"
    ),
    # Non-JSON garbage
    vcase(
        "Here is my advice: remove all leaves and spray everything.",
        "tomato__early_blight", "moderate", False, "JSON parsing"
    ),
]
# Add a validator-only test case entry
cases.append({
    "id": "validator_cases_batch",
    "description": "Validator check: good output, missing section, restricted chemical, unapproved target, severity mismatch, non-JSON",
    "input": req("tomato__early_blight"),
    "expected": pipeline.advise(req("tomato__early_blight")),
    "prompt_check": {"must_contain": []},
    "validator_cases": validator_only_cases,
})

# ------------------------------------------------------------------
# Group 5: Language localisation cases
# ------------------------------------------------------------------
for lang_code in ["hi", "te", "ta"]:
    r_lang = req("rice__blast", lang=lang_code, severity_band="moderate")
    expected_lang = pipeline.advise(r_lang)
    cases.append({
        "id": f"localisation_{lang_code}",
        "description": f"Response for rice blast in language '{lang_code}'",
        "input": r_lang,
        "expected": expected_lang,
        "prompt_check": {"must_contain": []},
        "validator_cases": [],
    })

# ------------------------------------------------------------------
# Group 6: Pest case
# ------------------------------------------------------------------
r_pest = req("pest__fall_armyworm", severity_band="severe", second_label="maize__healthy")
expected_pest = pipeline.advise(r_pest)
cases.append({
    "id": "pest_fall_armyworm_severe",
    "description": "Fall armyworm severe – chemical chlorantraniliprole allowed",
    "input": r_pest,
    "expected": expected_pest,
    "prompt_check": {"must_contain": ["fall_armyworm", "severe"]},
    "validator_cases": [],
})

# ------------------------------------------------------------------
# Write output
# ------------------------------------------------------------------
print(f"Generated {len(cases)} parity cases.")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
print(f"Written to {OUT_PATH}")
