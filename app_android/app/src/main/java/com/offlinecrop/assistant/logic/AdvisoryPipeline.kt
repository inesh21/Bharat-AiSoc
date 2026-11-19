package com.offlinecrop.assistant.logic

import org.json.JSONObject

/**
 * AdvisoryPipeline – Kotlin port of llm/pipeline.py (Phase 4.2).
 *
 * Orchestrates the full Contract 2 -> Contract 3 flow:
 *  1. Quality / unknown early exit
 *  2. Clarification check
 *  3. Knowledge retrieval
 *  4. LLM generation (optional) + validation
 *  5. Fallback if LLM unavailable or validation fails
 *  6. Language localisation
 *
 * Pure Kotlin – no Android imports.
 *
 * @param kbJson             Contents of kb.json asset.
 * @param rulesJson          Contents of rules.json asset.
 * @param clarificationsJson Contents of clarifications.json asset.
 * @param phrasesJson        Contents of phrases.json asset.
 * @param llmGenerate        Optional LLM function: (systemPrompt, userContent) -> rawText.
 *                           When null, the pipeline always uses the fallback template.
 */
class AdvisoryPipeline(
    kbJson: String,
    rulesJson: String,
    clarificationsJson: String,
    phrasesJson: String,
    private val llmGenerate: ((system: String, user: String) -> String)? = null
) {
    private val kb = KnowledgeRepository(kbJson, rulesJson)
    private val clarificationEngine = ClarificationEngine(clarificationsJson)
    private val validator = AdvisoryValidator(rulesJson)
    private val languageLayer = LanguageLayer(phrasesJson)

    /**
     * Processes a Contract 2 request (passed as a JSONObject) and returns
     * a Contract 3 [AdvisoryResponseData].
     *
     * @param request  The Contract 2 JSON.
     * @param onToken  Optional streaming callback, called once per token or
     *                 once per word when using the fallback.
     */
    fun advise(
        request: JSONObject,
        onToken: ((String) -> Unit)? = null
    ): AdvisoryResponseData {
        val vision = request.optJSONObject("vision") ?: JSONObject()
        val lang = request.optString("language", "en")
        val answersArr = request.optJSONArray("answers")

        val predictions = run {
            val arr = vision.optJSONArray("predictions") ?: return@run emptyList<ClarificationEngine.PredictionEntry>()
            (0 until arr.length()).map { i ->
                val p = arr.getJSONObject(i)
                ClarificationEngine.PredictionEntry(
                    label = p.getString("label"),
                    type = p.optString("type", "disease"),
                    confidence = p.getDouble("confidence").toFloat()
                )
            }
        }

        val severityBand = vision.optJSONObject("severity")?.optString("band", "moderate") ?: "moderate"

        // 1. Early exit for bad quality / unknown / no predictions
        if (vision.optBoolean("unknown", false) ||
            vision.optJSONObject("quality")?.optBoolean("ok", true) == false ||
            predictions.isEmpty()
        ) {
            val resp = kb.buildFallbackAdvisory("unknown", severityBand = "none", lang = lang)
            streamIfNeeded(resp, onToken)
            return resp
        }

        var currentPredictions = predictions

        // 2. Clarification check
        val answers = if (answersArr != null) {
            (0 until answersArr.length()).map { answersArr.getJSONObject(it) }
        } else emptyList()

        if (answers.isNotEmpty()) {
            val firstAnswer = answers[0]
            val ambiguity = clarificationEngine.checkAmbiguity(currentPredictions, lang = lang)
            if (ambiguity != null) {
                currentPredictions = clarificationEngine.applyAnswer(
                    pairKey = ambiguity.pairKey,
                    questionId = firstAnswer.optString("question_id", ""),
                    answer = firstAnswer.optString("answer", ""),
                    predictions = currentPredictions
                )
            }
        } else {
            val ambiguity = clarificationEngine.checkAmbiguity(currentPredictions, lang = lang)
            if (ambiguity != null) {
                return AdvisoryResponseData(
                    schemaVersion = "1.0",
                    status = "needs_clarification",
                    clarification = ClarificationData(
                        questionId = ambiguity.questionId,
                        text = ambiguity.text,
                        options = ambiguity.options
                    ),
                    diagnosis = "Ambiguous between ${currentPredictions[0].label} and ${currentPredictions[1].label}",
                    severityBand = severityBand,
                    actionsNow = emptyList(),
                    prevention = emptyList(),
                    seekHelp = false,
                    sourceIds = listOf("kb:${currentPredictions[0].label}", "kb:${currentPredictions[1].label}"),
                    usedFallback = false,
                    language = lang,
                    text = ambiguity.text
                )
            }
        }

        val conditionId = currentPredictions[0].label

        // 3. Knowledge retrieval
        val kbEntry = kb.getEntry(conditionId)
            ?: run {
                val resp = kb.buildFallbackAdvisory("unknown", severityBand = "none", lang = lang)
                streamIfNeeded(resp, onToken)
                return resp
            }

        // 4. LLM generation (if available) + validation
        var usedFallback = false
        var parsedOutput: JSONObject? = null

        if (llmGenerate != null) {
            val userContent = buildUserContent(vision, kbEntry, currentPredictions, severityBand, lang)
            val rawGeneration = llmGenerate.invoke(PromptBuilder.SYSTEM_PROMPT, userContent)

            val result = validator.validate(rawGeneration, conditionId, severityBand)
            if (result.isValid && result.parsed != null) {
                parsedOutput = result.parsed
            } else {
                usedFallback = true
            }
        } else {
            usedFallback = true
        }

        val response: AdvisoryResponseData = if (usedFallback || parsedOutput == null) {
            kb.buildFallbackAdvisory(conditionId, severityBand = severityBand, lang = lang)
        } else {
            val actArr = parsedOutput.optJSONArray("actions_now")
            val prevArr = parsedOutput.optJSONArray("prevention")
            AdvisoryResponseData(
                schemaVersion = "1.0",
                status = "final",
                clarification = null,
                diagnosis = parsedOutput.optString("diagnosis", conditionId),
                severityBand = severityBand,
                actionsNow = if (actArr != null) (0 until actArr.length()).map { actArr.getString(it) } else emptyList(),
                prevention = if (prevArr != null) (0 until prevArr.length()).map { prevArr.getString(it) } else emptyList(),
                seekHelp = conditionId == "unknown",
                sourceIds = listOf("kb:$conditionId"),
                usedFallback = false,
                language = lang,
                text = parsedOutput.optString("summary_text", "")
            )
        }

        // 5. Localisation
        val localised = languageLayer.localise(response, lang)

        streamIfNeeded(localised, onToken)
        return localised
    }

    private fun buildUserContent(
        vision: JSONObject,
        kbEntry: JSONObject,
        predictions: List<ClarificationEngine.PredictionEntry>,
        severityBand: String,
        lang: String
    ): String {
        val crop = vision.optString("crop", "unknown")
        val top = predictions.firstOrNull()
        val label = top?.label ?: "unknown"
        val confidence = top?.confidence ?: 0f

        val symptomArr = kbEntry.optJSONArray("symptoms")
        val symptoms = if (symptomArr != null) (0 until symptomArr.length()).map { symptomArr.getString(it) } else emptyList()

        val actsByBand = kbEntry.optJSONObject("severity_actions")
        val bandArr = actsByBand?.optJSONArray(severityBand) ?: actsByBand?.optJSONArray("moderate")
        val bandActions = if (bandArr != null) (0 until bandArr.length()).map { bandArr.getString(it) } else emptyList()

        val organicArr = kbEntry.optJSONArray("organic_options")
        val organicOptions = if (organicArr != null) (0 until organicArr.length()).map { organicArr.getString(it) } else emptyList()

        val chemArr = kbEntry.optJSONArray("chemical_options")
        val chemOptions = if (chemArr != null) {
            (0 until chemArr.length()).map { i ->
                val c = chemArr.getJSONObject(i)
                mapOf(
                    "name" to c.optString("name", ""),
                    "dose" to c.optString("dose", ""),
                    "phi_days" to c.optString("phi_days", "0"),
                    "safety" to c.optString("safety", "")
                )
            }
        } else emptyList()

        val prevArr = kbEntry.optJSONArray("prevention")
        val prevention = if (prevArr != null) (0 until prevArr.length()).map { prevArr.getString(it) } else emptyList()

        return PromptBuilder.buildAdvisoryUserContent(
            crop = crop,
            label = label,
            confidence = confidence,
            severityBand = severityBand,
            symptoms = symptoms,
            bandActions = bandActions,
            organicOptions = organicOptions,
            chemicalOptions = chemOptions,
            prevention = prevention,
            language = lang
        )
    }

    private fun streamIfNeeded(resp: AdvisoryResponseData, onToken: ((String) -> Unit)?) {
        if (onToken == null || resp.text.isBlank()) return
        resp.text.split(" ").forEach { word -> onToken("$word ") }
    }
}
