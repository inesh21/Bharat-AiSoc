package com.offlinecrop.assistant.engine

import android.graphics.Bitmap
import com.google.gson.annotations.SerializedName

// ==========================================
// CONTRACT 1: Vision Result
// ==========================================

data class QualityInfo(
    @SerializedName("ok") val ok: Boolean,
    @SerializedName("issues") val issues: List<String> = emptyList()
)

data class Prediction(
    @SerializedName("label") val label: String,
    @SerializedName("type") val type: String, // "disease" | "pest" | "deficiency" | "healthy"
    @SerializedName("confidence") val confidence: Float
)

data class SeverityInfo(
    @SerializedName("percent") val percent: Float,
    @SerializedName("band") val band: String // "none" | "mild" | "moderate" | "severe"
)

data class VisionResult(
    @SerializedName("schema_version") val schemaVersion: String = "1.0",
    @SerializedName("image_id") val imageId: String,
    @SerializedName("model_version") val modelVersion: String = "vision_v1",
    @SerializedName("quality") val quality: QualityInfo,
    @SerializedName("unknown") val unknown: Boolean,
    @SerializedName("crop") val crop: String,
    @SerializedName("predictions") val predictions: List<Prediction> = emptyList(),
    @SerializedName("severity") val severity: SeverityInfo? = null
)

// ==========================================
// CONTRACT 2: Advisory Request
// ==========================================

data class ClarificationAnswer(
    @SerializedName("question_id") val questionId: String,
    @SerializedName("answer") val answer: String // "yes" | "no" | "not_sure"
)

data class AdvisoryRequest(
    @SerializedName("schema_version") val schemaVersion: String = "1.0",
    @SerializedName("vision") val vision: VisionResult,
    @SerializedName("region") val region: String = "in_south",
    @SerializedName("language") val language: String = "en",
    @SerializedName("growth_stage") val growthStage: String = "unknown",
    @SerializedName("answers") val answers: List<ClarificationAnswer> = emptyList()
)

// ==========================================
// CONTRACT 3: Advisory Response
// ==========================================

data class ClarificationQuestion(
    @SerializedName("question_id") val questionId: String,
    @SerializedName("text") val text: String,
    @SerializedName("options") val options: List<String> = listOf("yes", "no", "not_sure")
)

data class AdvisoryResponse(
    @SerializedName("schema_version") val schemaVersion: String = "1.0",
    @SerializedName("status") val status: String = "final", // "final" | "needs_clarification"
    @SerializedName("clarification") val clarification: ClarificationQuestion? = null,
    @SerializedName("diagnosis") val diagnosis: String = "",
    @SerializedName("severity_band") val severityBand: String = "none",
    @SerializedName("actions_now") val actionsNow: List<String> = emptyList(),
    @SerializedName("prevention") val prevention: List<String> = emptyList(),
    @SerializedName("seek_help") val seekHelp: Boolean = false,
    @SerializedName("source_ids") val sourceIds: List<String> = emptyList(),
    @SerializedName("used_fallback") val usedFallback: Boolean = false,
    @SerializedName("language") val language: String = "en",
    @SerializedName("text") val text: String = ""
)

// ==========================================
// KOTLIN ENGINE INTERFACES (docs/CONTRACTS.md)
// ==========================================

interface VisionEngine {
    suspend fun analyze(bitmap: Bitmap): VisionResult
}

interface AdvisoryEngine {
    fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse
}

interface SpeechEngine {
    fun listen(lang: String): String
    fun speak(text: String, lang: String)
    fun stopSpeaking()
    fun isSpeaking(): Boolean
}
