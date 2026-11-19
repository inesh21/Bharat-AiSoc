package com.offlinecrop.assistant.logic

import org.json.JSONObject

/**
 * AdvisoryValidator – Kotlin port of llm/validator.py (Phase 4.2).
 *
 * NON-NEGOTIABLE CONSTRAINT (AGENTS.md):
 * "The LLM never decides chemicals or doses. Chemical names, doses, pre-harvest
 * intervals and safety text come only from knowledge/rules.yaml. The LLM may
 * explain them; the output validator rejects anything not in the rules table."
 *
 * Validates:
 *  1. Valid JSON
 *  2. Required sections present (diagnosis, actions_now, prevention, summary_text)
 *  3. No restricted/banned chemicals in generated text
 *  4. No chemicals prescribed for a condition they are not approved for
 *  5. No chemicals prescribed when severity level forbids them
 *
 * Pure Kotlin – no Android imports.
 */
class AdvisoryValidator(rulesJson: String) {

    private val rules = JSONObject(rulesJson)
    private val chemicalsObj = rules.optJSONObject("chemicals") ?: JSONObject()
    private val restrictedChemicals: Set<String>

    // All valid chemical tokens (key, trade names, active ingredient)
    private val validChemicalTokens: Set<String>

    init {
        val restricted = mutableSetOf<String>()
        val restrictedArr = rules.optJSONArray("restricted_chemicals")
        if (restrictedArr != null) {
            for (i in 0 until restrictedArr.length()) {
                restricted.add(restrictedArr.getString(i).lowercase())
            }
        }
        restrictedChemicals = restricted

        val tokens = mutableSetOf<String>()
        val keys = chemicalsObj.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            tokens.add(k.lowercase().replace("_", " "))
            val chem = chemicalsObj.getJSONObject(k)
            val names = chem.optJSONArray("trade_names")
            if (names != null) {
                for (i in 0 until names.length()) tokens.add(names.getString(i).lowercase())
            }
            tokens.add(chem.optString("active_ingredient", "").lowercase())
        }
        validChemicalTokens = tokens
    }

    data class ValidationResult(
        val isValid: Boolean,
        val parsed: JSONObject?,
        val rejectionReasons: List<String>
    )

    /**
     * Validates [llmOutputText] against the rules.
     * Mirrors llm/validator.py::OutputValidator.validate().
     */
    fun validate(
        llmOutputText: String,
        targetConditionId: String,
        severityBand: String = "moderate"
    ): ValidationResult {
        val reasons = mutableListOf<String>()

        // 1. Parse JSON
        val parsed: JSONObject
        try {
            var cleaned = llmOutputText.trim()
            if (cleaned.startsWith("```json")) cleaned = cleaned.removePrefix("```json")
            if (cleaned.endsWith("```")) cleaned = cleaned.removeSuffix("```")
            cleaned = cleaned.trim()
            parsed = JSONObject(cleaned)
        } catch (e: Exception) {
            return ValidationResult(false, null, listOf("JSON parsing error: ${e.message}"))
        }

        // 2. Required fields
        val required = listOf("diagnosis", "actions_now", "prevention", "summary_text")
        for (field in required) {
            if (!parsed.has(field) || parsed.optString(field, "").isBlank()) {
                reasons.add("Missing or empty required field: '$field'")
            }
        }
        if (reasons.isNotEmpty()) return ValidationResult(false, parsed, reasons)

        // 3. Build a single text blob for scanning
        val actionsArr = parsed.optJSONArray("actions_now")
        val prevArr = parsed.optJSONArray("prevention")
        val actionsText = (0 until (actionsArr?.length() ?: 0)).joinToString(" ") { actionsArr!!.getString(it) }
        val prevText = (0 until (prevArr?.length() ?: 0)).joinToString(" ") { prevArr!!.getString(it) }

        val fullText = "${parsed.optString("diagnosis", "")} $actionsText $prevText ${parsed.optString("summary_text", "")}".lowercase()

        // 4. Restricted chemicals
        for (restricted in restrictedChemicals) {
            val pattern = Regex("\\b${Regex.escape(restricted)}\\b")
            if (pattern.containsMatchIn(fullText)) {
                reasons.add("Restricted/banned chemical detected: '$restricted'")
            }
        }

        // 5. Approve-target and severity check
        val severityRule = rules.optJSONObject("severity_thresholds")
            ?.optJSONObject(severityBand) ?: JSONObject()
        val chemicalAllowed = severityRule.optBoolean("chemical_allowed", true)

        val chemKeys = chemicalsObj.keys()
        while (chemKeys.hasNext()) {
            val chemKey = chemKeys.next()
            val chemInfo = chemicalsObj.getJSONObject(chemKey)
            val targets = chemInfo.optJSONArray("approved_targets")
            val approvedTargets = if (targets != null) {
                (0 until targets.length()).map { targets.getString(it) }.toSet()
            } else emptySet()

            val tradeNames = chemInfo.optJSONArray("trade_names")
            val tokensToCheck = mutableListOf(chemKey.lowercase().replace("_", " "))
            if (tradeNames != null) {
                for (i in 0 until tradeNames.length()) tokensToCheck.add(tradeNames.getString(i).lowercase())
            }

            for (token in tokensToCheck) {
                val pattern = Regex("\\b${Regex.escape(token)}\\b")
                if (!pattern.containsMatchIn(fullText)) continue
                if (!chemicalAllowed) {
                    reasons.add("Chemical '$token' prescribed when severity is '$severityBand' (chemicals not permitted).")
                } else if (targetConditionId !in approvedTargets) {
                    reasons.add("Chemical '$token' is not an approved target for '$targetConditionId'.")
                }
            }
        }

        return ValidationResult(reasons.isEmpty(), parsed, reasons)
    }
}
