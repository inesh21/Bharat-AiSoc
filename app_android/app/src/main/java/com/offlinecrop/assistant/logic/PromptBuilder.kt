package com.offlinecrop.assistant.logic

/**
 * PromptBuilder – Kotlin port of llm/prompts.py (Phase 4.2).
 *
 * Builds Llama 3.2 chat-format prompts combining Contract 1 vision data
 * with retrieved knowledge-base facts.
 *
 * Pure Kotlin – no Android dependencies.
 */
object PromptBuilder {

    val SYSTEM_PROMPT: String = """You are an offline crop disease and agronomy advisor for smallholder farmers.
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
}"""

    /**
     * Wraps system + user content in Llama 3.2 chat template tokens.
     * Mirrors the format used in runbook section 5.4.
     */
    fun buildChatPrompt(systemText: String, userText: String): String {
        return "<|start_header_id|>system<|end_header_id|>\n\n$systemText<|eot_id|>" +
            "<|start_header_id|>user<|end_header_id|>\n\n$userText<|eot_id|>" +
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
    }

    /**
     * Builds the user-turn content for a specific advisory request.
     * Mirrors llm/prompts.py::build_advisory_prompt().
     *
     * @param crop         Crop name from vision result.
     * @param label        Top prediction label.
     * @param confidence   Top prediction confidence (0–1).
     * @param severityBand Severity band string.
     * @param symptoms     List of symptom strings from KB entry.
     * @param bandActions  Recommended actions for the given severity band.
     * @param organicOptions List of organic option strings.
     * @param chemicalOptions List of chemical option maps (name, dose, phi_days, safety).
     * @param prevention   List of prevention strings.
     * @param language     ISO language code.
     */
    fun buildAdvisoryUserContent(
        crop: String,
        label: String,
        confidence: Float,
        severityBand: String,
        symptoms: List<String>,
        bandActions: List<String>,
        organicOptions: List<String>,
        chemicalOptions: List<Map<String, String>>,
        prevention: List<String>,
        language: String = "en"
    ): String {
        val confPct = (confidence * 100).toInt()
        val symptomLines = symptoms.take(2).joinToString("\n") { "- $it" }
        val actionLines = bandActions.joinToString("\n") { "- $it" }
        val organicLines = organicOptions.joinToString("\n") { "- $it" }
        val chemLines = if (chemicalOptions.isEmpty()) {
            "None (Organic only)"
        } else {
            chemicalOptions.joinToString("\n") { c ->
                "- ${c["name"]}: ${c["dose"]} (Pre-harvest interval: ${c["phi_days"]} days). Safety: ${c["safety"]}"
            }
        }
        val prevLines = prevention.take(3).joinToString("\n") { "- $it" }

        return """PATIENT CASE:
- Crop: $crop
- Identified condition: $label (confidence: $confPct%)
- Assessed severity: $severityBand
- Target language: $language

GROUND TRUTH REFERENCE FACTS:
Symptoms:
$symptomLines

Recommended Actions for $severityBand severity:
$actionLines

Approved Organic Options:
$organicLines

Approved Chemical Options (Do NOT modify dose or safety text):
$chemLines

Prevention Practices:
$prevLines

Generate the JSON response for this farmer case following all safety rules."""
    }
}
