package com.offlinecrop.assistant.logic

import org.json.JSONArray
import org.json.JSONObject

/**
 * KnowledgeRepository – Kotlin port of knowledge/retrieval.py (Phase 4.2).
 *
 * Loads kb.json and rules.json from raw strings (passed in by the caller,
 * which reads them from Android assets).  Pure Kotlin – no Android imports.
 */
class KnowledgeRepository(
    kbJson: String,
    rulesJson: String
) {
    // Map from condition_id -> entry object
    private val entries: Map<String, JSONObject>

    // Rules data
    private val rules: JSONObject

    // Approved chemicals keyed by id
    private val chemicals: JSONObject

    // Restricted chemical names (lowercase)
    private val restrictedChemicals: Set<String>

    init {
        val arr = JSONArray(kbJson)
        val mutable = mutableMapOf<String, JSONObject>()
        for (i in 0 until arr.length()) {
            val obj = arr.getJSONObject(i)
            mutable[obj.getString("id")] = obj
        }
        entries = mutable

        rules = JSONObject(rulesJson)
        chemicals = rules.optJSONObject("chemicals") ?: JSONObject()

        val restricted = mutableSetOf<String>()
        val restrictedArr = rules.optJSONArray("restricted_chemicals") ?: JSONArray()
        for (i in 0 until restrictedArr.length()) {
            restricted.add(restrictedArr.getString(i).lowercase())
        }
        restrictedChemicals = restricted
    }

    /** Returns the KB entry for [conditionId], or null if absent. */
    fun getEntry(conditionId: String): JSONObject? = entries[conditionId]

    /**
     * Returns approved chemicals from rules.json whose approved_targets
     * contain [targetId].
     */
    fun getApprovedChemicalsFor(targetId: String): List<JSONObject> {
        val result = mutableListOf<JSONObject>()
        val keys = chemicals.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val chem = chemicals.getJSONObject(key)
            val targets = chem.optJSONArray("approved_targets") ?: continue
            for (i in 0 until targets.length()) {
                if (targets.getString(i) == targetId) {
                    val out = JSONObject(chem.toString())
                    out.put("id", key)
                    result.add(out)
                    break
                }
            }
        }
        return result
    }

    fun getRestrictedChemicals(): Set<String> = restrictedChemicals

    /**
     * Builds a deterministic, 100% verified fallback advisory directly from
     * the knowledge base and rules, with no LLM involvement.
     * Mirrors knowledge/retrieval.py::build_fallback_advisory().
     */
    fun buildFallbackAdvisory(
        conditionId: String,
        severityBand: String = "moderate",
        lang: String = "en"
    ): AdvisoryResponseData {
        val entry = if (conditionId == "unknown") null else getEntry(conditionId)

        if (entry == null) {
            return AdvisoryResponseData(
                schemaVersion = "1.0",
                status = "final",
                clarification = null,
                diagnosis = "Condition Unknown or Inconclusive",
                severityBand = severityBand,
                actionsNow = listOf(
                    "Do not apply unverified chemical sprays.",
                    "Collect a fresh physical leaf sample in a clean paper bag.",
                    "Consult your nearest Krishi Vigyan Kendra (KVK) or State Agricultural Department officer."
                ),
                prevention = listOf("Inspect surrounding plants and maintain general field sanitation."),
                seekHelp = true,
                sourceIds = listOf("kb:unknown"),
                usedFallback = true,
                language = lang,
                text = "The condition could not be conclusively identified. Please consult your local agricultural extension officer."
            )
        }

        // Severity-filtered actions
        val actsByBand = entry.optJSONObject("severity_actions") ?: JSONObject()
        val bandArr = actsByBand.optJSONArray(severityBand)
            ?: actsByBand.optJSONArray("moderate")
            ?: JSONArray()

        val severityRule = rules.optJSONObject("severity_thresholds")
            ?.optJSONObject(severityBand) ?: JSONObject()
        val chemicalAllowed = severityRule.optBoolean("chemical_allowed", true)

        val rawActions = (0 until bandArr.length()).map { bandArr.getString(it) }
        val actionsNow = if (!chemicalAllowed) {
            rawActions.filter { a ->
                !a.contains("WP") && !a.contains("EC") && !"fungicide".let { a.lowercase().contains(it) }
            }
        } else rawActions

        val prevArr = entry.optJSONArray("prevention") ?: JSONArray()
        val prevention = (0 until prevArr.length()).map { prevArr.getString(it) }

        val conditionName = conditionId
            .replace("__", " - ")
            .replace("_", " ")
            .split(" ").joinToString(" ") { it.replaceFirstChar(Char::uppercaseChar) }

        val firstAction = actionsNow.firstOrNull() ?: "Scout fields."
        val fullText = "Diagnosis: $conditionName. Severity: ${severityBand.replaceFirstChar(Char::uppercaseChar)}. Immediate action: $firstAction"

        return AdvisoryResponseData(
            schemaVersion = "1.0",
            status = "final",
            clarification = null,
            diagnosis = conditionName,
            severityBand = severityBand,
            actionsNow = actionsNow,
            prevention = prevention,
            seekHelp = conditionId == "unknown",
            sourceIds = listOf("kb:$conditionId"),
            usedFallback = true,
            language = lang,
            text = fullText
        )
    }
}

/** Plain data carrier (no Android dependencies) for Contract 3. */
data class AdvisoryResponseData(
    val schemaVersion: String = "1.0",
    val status: String = "final",
    val clarification: ClarificationData? = null,
    val diagnosis: String = "",
    val severityBand: String = "none",
    val actionsNow: List<String> = emptyList(),
    val prevention: List<String> = emptyList(),
    val seekHelp: Boolean = false,
    val sourceIds: List<String> = emptyList(),
    val usedFallback: Boolean = false,
    val language: String = "en",
    val text: String = ""
)

data class ClarificationData(
    val questionId: String,
    val text: String,
    val options: List<String> = listOf("yes", "no", "not_sure")
)
