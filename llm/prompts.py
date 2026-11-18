"""Prompt templates and context builder for Llama 3.2 1B/3B (Tasks B6 & B7).

Maintains strict context budget (600 - 1200 tokens) and enforces agricultural safety rules:
- No invented chemicals or doses
- Only use provided knowledge context
- Short, actionable sentences
- Structured JSON output target
"""

from typing import Dict, Any, List


SYSTEM_PROMPT = """You are an offline crop disease and agronomy advisor for smallholder farmers.
Your advice must be concise, practical, and strictly grounded in the provided reference facts.

CRITICAL SAFETY RULES:
1. NEVER invent chemicals, fungicides, insecticides, or dosages. Use ONLY products and doses explicitly listed in the reference facts.
2. If severity is mild or healthy, prioritize cultural practices, pruning, and organic bio-formulations. Do not prescribe harsh chemicals unless severity is moderate or severe and listed in reference facts.
3. Keep sentences short, simple, and direct. Avoid jargon.
4. If the condition is unknown or confidence is low, advise consulting a local agricultural extension officer (KVK) and do not guess.

You must respond in JSON adhering to this exact format:
{
  "diagnosis": "<Crop and disease/pest name>",
  "actions_now": ["<Action 1>", "<Action 2>"],
  "prevention": ["<Prevention 1>", "<Prevention 2>"],
  "summary_text": "<Clear 2-3 sentence explanation for farmer and voice TTS>"
}
"""


def build_advisory_prompt(
    vision_result: Dict[str, Any],
    kb_entry: Dict[str, Any],
    severity_band: str = "moderate",
    region: str = "in_pan_india",
    language: str = "en"
) -> str:
    """Builds a token-efficient prompt combining Contract 1 Vision Result and retrieved KB facts."""
    crop = vision_result.get("crop", "unknown")
    top_pred = vision_result.get("predictions", [{}])[0]
    label = top_pred.get("label", "unknown")
    conf = top_pred.get("confidence", 0.0)

    # Reference facts
    symptoms = kb_entry.get("symptoms", [])
    actions_by_sev = kb_entry.get("severity_actions", {})
    band_actions = actions_by_sev.get(severity_band, actions_by_sev.get("moderate", []))
    organic = kb_entry.get("organic_options", [])
    chemicals = kb_entry.get("chemical_options", [])
    prevention = kb_entry.get("prevention", [])

    chem_lines = []
    for c in chemicals:
        chem_lines.append(f"- {c.get('name')}: {c.get('dose')} (Pre-harvest interval: {c.get('phi_days')} days). Safety: {c.get('safety')}")

    user_content = f"""PATIENT CASE:
- Crop: {crop}
- Identified condition: {label} (confidence: {conf * 100:.0f}%)
- Assessed severity: {severity_band}
- Target language: {language}

GROUND TRUTH REFERENCE FACTS:
Symptoms:
{chr(10).join('- ' + s for s in symptoms[:2])}

Recommended Actions for {severity_band} severity:
{chr(10).join('- ' + a for a in band_actions)}

Approved Organic Options:
{chr(10).join('- ' + o for o in organic)}

Approved Chemical Options (Do NOT modify dose or safety text):
{chr(10).join(chem_lines) if chem_lines else 'None (Organic only)'}

Prevention Practices:
{chr(10).join('- ' + p for p in prevention[:3])}

Generate the JSON response for this farmer case following all safety rules."""

    return user_content
