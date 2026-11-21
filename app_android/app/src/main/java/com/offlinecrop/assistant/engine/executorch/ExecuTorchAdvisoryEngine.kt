package com.offlinecrop.assistant.engine.executorch

import android.content.Context
import android.util.Log
import com.offlinecrop.assistant.engine.*
import com.offlinecrop.assistant.logic.*
import org.json.JSONObject
import org.pytorch.executorch.extension.llm.LlmCallback
import org.pytorch.executorch.extension.llm.LlmModule
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/**
 * ExecuTorch-based advisory engine using Llama 3.2 1B Instruct.
 *
 * Uses org.pytorch.executorch.extension.llm.LlmModule from the prebuilt AAR.
 * Integrates with AdvisoryPipeline (Kotlin logic) for knowledge retrieval,
 * validation, and language layer.
 *
 * Contract: Implements AdvisoryEngine per CONTRACTS.md Section 4
 * Model: Llama-3.2-1B-Instruct, 8da4w quantization, max_seq_length 1024
 */
class ExecuTorchAdvisoryEngine(
    private val context: Context,
    private val modelDir: File
) : AdvisoryEngine {

    private val TAG = "ExecuTorchAdvisory"

    // Advisory pipeline (Kotlin logic)
    private val advisoryPipeline: AdvisoryPipeline
    private val validator: AdvisoryValidator

    private var llmModule: LlmModule? = null
    private val stopRequested = AtomicBoolean(false)

    init {
        // Load advisory logic components by reading JSON assets
        // AssetManager.open() already looks in the assets/ directory, so no prefix needed
        val kbJson = context.assets.open("kb.json").bufferedReader().use { it.readText() }
        val rulesJson = context.assets.open("rules.json").bufferedReader().use { it.readText() }
        val clarificationsJson = context.assets.open("clarifications.json").bufferedReader().use { it.readText() }
        val phrasesJson = context.assets.open("phrases.json").bufferedReader().use { it.readText() }

        advisoryPipeline = AdvisoryPipeline(
            kbJson = kbJson,
            rulesJson = rulesJson,
            clarificationsJson = clarificationsJson,
            phrasesJson = phrasesJson,
            llmGenerate = null // We'll use AdvisoryPipeline for non-LLM logic only
        )

        validator = AdvisoryValidator(rulesJson)

        loadModel()
    }

    private fun loadModel() {
        try {
            val modelPath = File(modelDir, "llama32_1b.pte").absolutePath
            val tokenizerPath = File(modelDir, "tokenizer.model").absolutePath

            if (!File(modelPath).exists()) {
                throw IllegalStateException("Llama model not found: $modelPath")
            }
            if (!File(tokenizerPath).exists()) {
                throw IllegalStateException("Tokenizer not found: $tokenizerPath")
            }

            // Create LlmModule - loads in constructor, no separate load() call needed
            // Constructor: LlmModule(modelPath: String, tokenizerPath: String, temperature: Float)
            llmModule = LlmModule(modelPath, tokenizerPath, 0.3f)

            Log.i(TAG, "Llama module loaded successfully from $modelPath")

        } catch (e: Exception) {
            Log.e(TAG, "Model load failed: ${e.message}", e)
            throw e
        }
    }

    override fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse {
        return try {
            // Convert request to JSONObject for pipeline processing
            val requestJson = convertRequestToJson(req)

            // Check if clarification is needed (pipeline handles this)
            val clarificationCheck = advisoryPipeline.advise(requestJson, null)
            if (clarificationCheck.status == "needs_clarification") {
                return convertResponseFromJson(clarificationCheck)
            }

            // Build prompt using Llama 3.2 chat format
            val prompt = buildLlama32Prompt(req)

            // Check prompt length (our model has max_seq_length 1024)
            // Rough estimate: ~4 chars per token, keep prompt + output within 1024
            if (prompt.length > 2000) {  // ~500 tokens
                Log.w(TAG, "Prompt too long: ${prompt.length} chars. May truncate output.")
            }

            // Reset context before each scan
            llmModule?.resetNative()
            stopRequested.set(false)

            // Generate response using LLM
            val generatedText = AtomicReference<String>("")
            val stats = AtomicReference<String>("")
            val error = AtomicReference<String?>(null)

            val callback = object : LlmCallback {
                override fun onResult(token: String) {
                    generatedText.set(generatedText.get() + token)
                    onToken(token)
                }

                override fun onStats(statsJson: String) {
                    stats.set(statsJson)
                    // Parse and log TTFT and tokens/s
                    try {
                        val statsObj = JSONObject(statsJson)
                        val ttft = statsObj.optDouble("time_to_first_token_ms", -1.0)
                        val tokensPerSec = statsObj.optDouble("tokens_per_second", -1.0)
                        Log.i(TAG, "LLM Stats: TTFT=${ttft}ms, tokens/s=$tokensPerSec")
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to parse stats: ${e.message}")
                    }
                }

                override fun onError(errorCode: Int, errorMsg: String) {
                    error.set("[$errorCode] $errorMsg")
                    Log.e(TAG, "LLM error: code=$errorCode, msg=$errorMsg")
                }
            }

            // Run generation - this is synchronous and blocks until complete
            llmModule?.generate(prompt, callback)

            // Check for errors
            error.get()?.let {
                throw RuntimeException("LLM generation error: $it")
            }

            val rawText = generatedText.get()

            // Validate output
            val topLabel = req.vision.predictions.firstOrNull()?.label ?: "unknown"
            val severityBand = req.vision.severity?.band ?: "moderate"
            val validationResult = validator.validate(rawText, topLabel, severityBand)

            if (!validationResult.isValid) {
                Log.w(TAG, "Validation failed: ${validationResult.rejectionReasons}. Using fallback.")
                // Use template fallback from pipeline
                return useFallbackTemplate(req)
            }

            // Parse validated JSON response
            val parsed = validationResult.parsed!!
            val actionsArr = parsed.optJSONArray("actions_now")
            val actionsNow = if (actionsArr != null) {
                (0 until actionsArr.length()).map { actionsArr.getString(it) }
            } else emptyList()

            val prevArr = parsed.optJSONArray("prevention")
            val prevention = if (prevArr != null) {
                (0 until prevArr.length()).map { prevArr.getString(it) }
            } else emptyList()

            AdvisoryResponse(
                status = "final",
                diagnosis = parsed.optString("diagnosis", "Unknown condition"),
                severityBand = severityBand,
                actionsNow = actionsNow,
                prevention = prevention,
                seekHelp = parsed.optBoolean("seek_help", false),
                sourceIds = listOf("kb:$topLabel"),
                usedFallback = false,
                language = req.language,
                text = parsed.optString("summary_text", rawText)
            )

        } catch (e: Exception) {
            Log.e(TAG, "Advisory generation failed: ${e.message}", e)
            useFallbackTemplate(req)
        }
    }

    private fun buildLlama32Prompt(req: AdvisoryRequest): String {
        // Llama 3.2 chat format (omit <|begin_of_text|> to avoid double BOS)
        // Format: <|start_header_id|>system<|end_header_id|>
        //         {system}<|eot_id|><|start_header_id|>user<|end_header_id|>
        //         {user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

        val systemPrompt = """You are an agricultural advisor. Provide practical advice for crop disease management.
Focus on:
1. Immediate actions (cultural/organic methods first)
2. Prevention strategies
3. When to seek professional help

Output as JSON with fields: diagnosis, actions_now (array), prevention (array), seek_help (boolean), summary_text."""

        val userContent = buildUserContent(req)

        val prompt = """<|start_header_id|>system<|end_header_id|>
$systemPrompt<|eot_id|><|start_header_id|>user<|end_header_id|>
$userContent<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

        return prompt
    }

    private fun buildUserContent(req: AdvisoryRequest): String {
        val vision = req.vision
        val topPred = vision.predictions.firstOrNull()
        val label = topPred?.label ?: "unknown"
        val confidence = topPred?.confidence ?: 0f
        val severity = vision.severity?.band ?: "none"

        return """Crop: ${vision.crop}
Condition: $label (confidence: ${confidence * 100}%)
Severity: $severity

Provide immediate actions and prevention strategies as JSON."""
    }

    private fun useFallbackTemplate(req: AdvisoryRequest): AdvisoryResponse {
        // Use pipeline's fallback template
        val requestJson = convertRequestToJson(req)
        val fallback = advisoryPipeline.advise(requestJson, null)
        return convertResponseFromJson(fallback).copy(usedFallback = true)
    }

    private fun convertRequestToJson(req: AdvisoryRequest): JSONObject {
        val json = JSONObject()
        json.put("schema_version", req.schemaVersion)
        json.put("language", req.language)
        json.put("region", req.region)
        json.put("growth_stage", req.growthStage)

        // Vision object
        val visionJson = JSONObject()
        visionJson.put("schema_version", req.vision.schemaVersion)
        visionJson.put("image_id", req.vision.imageId)
        visionJson.put("model_version", req.vision.modelVersion)
        visionJson.put("unknown", req.vision.unknown)
        visionJson.put("crop", req.vision.crop)

        // Quality
        val qualityJson = JSONObject()
        qualityJson.put("ok", req.vision.quality.ok)
        qualityJson.put("issues", org.json.JSONArray(req.vision.quality.issues))
        visionJson.put("quality", qualityJson)

        // Predictions
        val predictionsArray = org.json.JSONArray()
        req.vision.predictions.forEach { pred ->
            val predJson = JSONObject()
            predJson.put("label", pred.label)
            predJson.put("type", pred.type)
            predJson.put("confidence", pred.confidence)
            predictionsArray.put(predJson)
        }
        visionJson.put("predictions", predictionsArray)

        // Severity
        req.vision.severity?.let { sev ->
            val sevJson = JSONObject()
            sevJson.put("percent", sev.percent)
            sevJson.put("band", sev.band)
            visionJson.put("severity", sevJson)
        }

        json.put("vision", visionJson)

        // Answers
        if (req.answers.isNotEmpty()) {
            val answersArray = org.json.JSONArray()
            req.answers.forEach { ans ->
                val ansJson = JSONObject()
                ansJson.put("question_id", ans.questionId)
                ansJson.put("answer", ans.answer)
                answersArray.put(ansJson)
            }
            json.put("answers", answersArray)
        }

        return json
    }

    private fun convertResponseFromJson(response: AdvisoryResponseData): AdvisoryResponse {
        return AdvisoryResponse(
            schemaVersion = response.schemaVersion,
            status = response.status,
            clarification = response.clarification?.let { clar ->
                ClarificationQuestion(
                    questionId = clar.questionId,
                    text = clar.text,
                    options = clar.options
                )
            },
            diagnosis = response.diagnosis,
            severityBand = response.severityBand,
            actionsNow = response.actionsNow,
            prevention = response.prevention,
            seekHelp = response.seekHelp,
            sourceIds = response.sourceIds,
            usedFallback = response.usedFallback,
            language = response.language,
            text = response.text
        )
    }

    fun release() {
        llmModule?.close()  // Use close() not destroy()
        llmModule = null
        Log.i(TAG, "Llama module released")
    }
}
