package com.offlinecrop.assistant.engine.executorch

import android.content.Context
import android.os.SystemClock
import android.util.Log
import com.offlinecrop.assistant.engine.AdvisoryEngine
import com.offlinecrop.assistant.engine.AdvisoryRequest
import com.offlinecrop.assistant.engine.AdvisoryResponse
import com.offlinecrop.assistant.engine.ClarificationQuestion
import com.offlinecrop.assistant.logic.AdvisoryPipeline
import com.offlinecrop.assistant.logic.LanguageLayer
import com.offlinecrop.assistant.logic.PromptBuilder
import org.json.JSONArray
import org.json.JSONObject
import org.pytorch.executorch.extension.llm.LlmCallback
import org.pytorch.executorch.extension.llm.LlmModule
import java.io.File

internal data class GenerationMetrics(
    val callbacks: Int,
    val wallTtftMs: Long?,
    val decodeTokensPerSecond: Double?,
    val elapsedMs: Long,
    val accepted: Boolean,
)

internal class ExecuTorchAdvisoryEngine(
    context: Context,
    private val modelDir: File,
) : AdvisoryEngine, AutoCloseable {
    private val assets = context.applicationContext.assets
    private fun readAsset(name: String) =
        assets.open(name).bufferedReader().use { it.readText() }

    private val curated = JSONObject(readAsset("demo_ipm.json"))
    private val phrases = readAsset("phrases.json")
    private val languageLayer = LanguageLayer(phrases)
    private val pipeline = AdvisoryPipeline(
        readAsset("kb.json"),
        readAsset("rules.json"),
        readAsset("clarifications.json"),
        phrases,
    )
    private var native: LlmModule? = null
    var lastGeneration: GenerationMetrics? = null
        private set

    override fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse {
        lastGeneration = null
        val prepared = pipeline.advise(req.toContractJson())
        val question = prepared.clarification
        if (question != null) {
            return AdvisoryResponse(
                status = prepared.status,
                clarification = ClarificationQuestion(question.questionId, question.text, question.options),
                language = req.language,
                text = question.text,
                sourceIds = prepared.sourceIds,
                severityBand = prepared.severityBand,
            )
        }
        val source = prepared.sourceIds.singleOrNull()
        val condition = source?.removePrefix("kb:")
        val facts = condition?.let { curated.optJSONObject(it) }
        if (facts == null || prepared.seekHelp || req.answers.any { it.answer == "not_sure" }) {
            return AdvisoryResponse(

                seekHelp = true,
                sourceIds = listOf("kb:unknown"),
                usedFallback = true,
                language = req.language,
                text = languageLayer.phrase(req.language, "unknown_warning"),
            )
        }

        val english = facts.getJSONObject("en")
        val display = facts.optJSONObject(req.language) ?: english
        val actions = english.getJSONArray("actions")
        val choices = (0 until actions.length()).joinToString("\n") { "$it. " + actions.getString(it) }
        val system = "Select the most useful first action from this approved list. " +
            "Return only a JSON object with an integer action index, for example {\"action\":0}."
        val prompt = PromptBuilder.buildChatPrompt(
            system,
            "Condition: " + english.getString("diagnosis") + "\nSeverity: " +
                (req.vision.severity?.band ?: "unavailable") + "\nApproved actions:\n" + choices,
        )
        val selected = generateChoice(prompt + ACTION_PREFIX, actions.length())
        val displayActions = display.getJSONArray("actions")
        val primary = selected ?: 0
        val ordered = (listOf(primary) + (0 until displayActions.length()).filter { it != primary })
            .map(displayActions::getString)
        val diagnosis = display.getString("diagnosis")
        val prevention = display.getString("prevention")
        val text = listOf(
            languageLayer.phrase(req.language, "diagnosis_prefix") + " " + diagnosis + ".",
            languageLayer.phrase(req.language, "actions_prefix") + " " + ordered.joinToString(" "),
            languageLayer.phrase(req.language, "prevention_prefix") + " " + prevention,
        ).joinToString(" ")
        onToken(text)
        return AdvisoryResponse(
            diagnosis = diagnosis,
            severityBand = req.vision.severity?.band ?: "none",
            actionsNow = ordered,
            prevention = listOf(prevention),
            sourceIds = listOf("kb:$condition"),
            usedFallback = selected == null,
            language = req.language,
            text = text,
        )
    }

    private fun generateChoice(prompt: String, actionCount: Int): Int? {
        val started = SystemClock.elapsedRealtime()
        val raw = StringBuilder()
        var callbacks = 0
        var ttft: Long? = null
        var tokensPerSecond: Double? = null
        var failed = false
        val callback = object : LlmCallback {
            override fun onResult(token: String) {
                if (token.isEmpty()) return
                if (ttft == null) ttft = SystemClock.elapsedRealtime() - started
                callbacks++
                raw.append(token)
                if (parseActionChoice(ACTION_PREFIX + raw, actionCount) != null ||
                    callbacks >= MAX_RESPONSE_CALLBACKS
                ) {
                    native?.stop()
                }
            }

            override fun onStats(statsJson: String) {
                tokensPerSecond = runCatching {
                    JSONObject(statsJson).optDouble("decode_token_per_sec").takeIf(Double::isFinite)
                }.getOrNull()
            }

            override fun onError(errorCode: Int, errorMsg: String) {
                failed = true
                Log.e(TAG, "ExecuTorch generation error $errorCode: $errorMsg")
            }
        }
        try {
            val runtime = native ?: LlmModule(
                File(modelDir, "llama32_1b.pte").absolutePath,
                File(modelDir, "tokenizer.model").absolutePath,
                0f,
            ).also { native = it }
            runtime.resetContext()
            runtime.generate(prompt, MAX_SEQUENCE_LENGTH, callback, false)
        } catch (e: Exception) {
            failed = true
            Log.e(TAG, "Llama unavailable. Using grounded template.", e)
            close()
        } catch (e: OutOfMemoryError) {
            failed = true
            Log.e(TAG, "Insufficient memory for Llama. Using grounded template.", e)
            close()
        }
        val selected = if (failed) null else parseActionChoice(ACTION_PREFIX + raw, actionCount)
        lastGeneration = GenerationMetrics(
            callbacks, ttft, tokensPerSecond, SystemClock.elapsedRealtime() - started, selected != null,
        )
        return selected
    }

    override fun close() {
        native?.close()
        native = null
    }

    private companion object {
        const val TAG = "ExecuTorchAdvisory"
        const val MAX_SEQUENCE_LENGTH = 192
        const val MAX_RESPONSE_CALLBACKS = 12
        const val ACTION_PREFIX = "{\"action\":"
    }
}

private val ACTION_CHOICE = Regex("""\{\s*"action"\s*:\s*(0|[1-9]\d*)\s*\}""")

internal fun parseActionChoice(generation: String, actionCount: Int): Int? {
    val body = generation.trim().removeSuffix("<|eot_id|>").trim()
    return ACTION_CHOICE.matchEntire(body)?.groupValues?.get(1)?.toIntOrNull()
        ?.takeIf { it in 0 until actionCount }
}

private fun AdvisoryRequest.toContractJson() = JSONObject().apply {
    put("schema_version", schemaVersion)
    put("language", language)
    put("region", region)
    put("growth_stage", growthStage)
    put("answers", JSONArray(answers.map { answer ->
        JSONObject().put("question_id", answer.questionId).put("answer", answer.answer)
    }))
    put("vision", JSONObject().apply {
        put("schema_version", vision.schemaVersion)
        put("image_id", vision.imageId)
        put("model_version", vision.modelVersion)
        put("crop", vision.crop)
        put("unknown", vision.unknown)
        put("quality", JSONObject()
            .put("ok", vision.quality.ok)
            .put("issues", JSONArray(vision.quality.issues)))
        put("predictions", JSONArray(vision.predictions.map { prediction ->
            JSONObject().put("label", prediction.label)
                .put("type", prediction.type)
                .put("confidence", prediction.confidence.toDouble())
        }))
        put("severity", vision.severity?.let {
            JSONObject().put("percent", it.percent.toDouble()).put("band", it.band)
        } ?: JSONObject.NULL)
    })
}
