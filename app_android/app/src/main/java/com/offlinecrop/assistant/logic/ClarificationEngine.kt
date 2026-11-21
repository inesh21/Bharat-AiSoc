package com.offlinecrop.assistant.logic

import org.json.JSONArray
import org.json.JSONObject

/**
 * ClarificationEngine – Kotlin port of knowledge/clarifications.py (Phase 4.2).
 *
 * Evaluates whether the top-2 vision predictions are within a confidence
 * delta and, if a matching question pair exists, returns the clarifying
 * question.  Also applies farmer answers to re-weight predictions.
 *
 * Pure Kotlin – no Android imports.
 */
class ClarificationEngine(clarificationsJson: String) {

    // pairs keyed by pair_key (e.g. "tomato_early_blight_vs_septoria")
    private val pairs: JSONObject

    init {
        val root = JSONObject(clarificationsJson)
        pairs = root.optJSONObject("pairs") ?: JSONObject()
    }

    /**
     * Data class for a prediction entry.
     * Mirrors the Contract 1 prediction shape.
     */
    data class PredictionEntry(val label: String, val type: String, val confidence: Float)

    data class ClarificationResult(
        val questionId: String,
        val text: String,
        val options: List<String>,
        val pairKey: String
    )

    /**
     * Checks whether the top-2 predictions are ambiguous (delta < threshold)
     * and returns a clarifying question if a matching pair is configured.
     *
     * Mirrors ClarificationEngine.check_ambiguity() in Python.
     */
    fun checkAmbiguity(
        predictions: List<PredictionEntry>,
        confidenceThresholdDelta: Float = 0.15f,
        lang: String = "en"
    ): ClarificationResult? {
        if (predictions.size < 2) return null

        val top1 = predictions[0]
        val top2 = predictions[1]
        val delta = top1.confidence - top2.confidence
        if (delta >= confidenceThresholdDelta) return null

        val labels = setOf(top1.label, top2.label)

        val pairKeys = pairs.keys()
        while (pairKeys.hasNext()) {
            val pairKey = pairKeys.next()
            val pairInfo = pairs.getJSONObject(pairKey)
            val classesArr = pairInfo.optJSONArray("classes") ?: continue
            val pairClasses = (0 until classesArr.length()).map { classesArr.getString(it) }.toSet()
            if (labels != pairClasses) continue

            val questions = pairInfo.optJSONArray("questions") ?: continue
            if (questions.length() == 0) continue
            val q = questions.getJSONObject(0)

            val textObj = q.optJSONObject("text") ?: JSONObject()
            val qText = textObj.optString(lang, textObj.optString("en", ""))

            val optionsArr = q.optJSONArray("options") ?: JSONArray()
            val options = (0 until optionsArr.length()).map { optionsArr.getString(it) }

            return ClarificationResult(
                questionId = q.getString("question_id"),
                text = qText,
                options = options,
                pairKey = pairKey
            )
        }
        return null
    }

    /**
     * Applies the farmer's clarification answer to re-weight the predictions.
     * Mirrors ClarificationEngine.apply_answer() in Python.
     */
    fun applyAnswer(
        pairKey: String,
        questionId: String,
        answer: String,
        predictions: List<PredictionEntry>
    ): List<PredictionEntry> {
        val pairInfo = pairs.optJSONObject(pairKey) ?: return predictions
        val questions = pairInfo.optJSONArray("questions") ?: return predictions

        for (i in 0 until questions.length()) {
            val q = questions.getJSONObject(i)
            if (q.getString("question_id") != questionId) continue

            val adjustments = q.optJSONObject("weight_adjustments")
                ?.optJSONObject(answer) ?: JSONObject()

            val adjusted = predictions.map { p ->
                val adj = adjustments.optDouble(p.label, 0.0).toFloat()
                val newConf = (p.confidence + adj).coerceIn(0.01f, 0.99f)
                p.copy(confidence = Math.round(newConf * 100) / 100f)
            }
            return adjusted.sortedByDescending { it.confidence }
        }
        return predictions
    }
}
