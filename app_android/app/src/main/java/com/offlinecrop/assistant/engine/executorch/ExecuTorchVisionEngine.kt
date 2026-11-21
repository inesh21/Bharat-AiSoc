package com.offlinecrop.assistant.engine.executorch

import android.graphics.Bitmap
import android.graphics.Color
import com.offlinecrop.assistant.engine.Prediction
import com.offlinecrop.assistant.engine.QualityInfo
import com.offlinecrop.assistant.engine.SeverityInfo
import com.offlinecrop.assistant.engine.VisionEngine
import com.offlinecrop.assistant.engine.VisionResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.pytorch.executorch.EValue
import org.pytorch.executorch.Module
import org.pytorch.executorch.Tensor
import java.io.File
import java.util.UUID
import kotlin.math.exp
import kotlin.math.round

internal class ExecuTorchVisionEngine(modelDir: File) : VisionEngine, AutoCloseable {
    private val config = JSONObject(File(modelDir, "vision_v1.json").readText())
    private val labels = config.getJSONArray("labels").let { array ->
        List(array.length()) { array.getString(it) }
    }
    private val width = config.getJSONArray("image_size").getInt(0)
    private val height = config.getJSONArray("image_size").getInt(1)
    private val normalization = config.getJSONObject("normalization")
    private val mean = FloatArray(3) { normalization.getJSONArray("mean").getDouble(it).toFloat() }
    private val std = FloatArray(3) { normalization.getJSONArray("std").getDouble(it).toFloat() }
    private val temperature = config.getDouble("temperature").toFloat()
    private val threshold = config.getDouble("ood_threshold")
    private val modelVersion = config.getString("model_name")
    private val module by lazy {
        val file = File(modelDir, "vision_v1.pte")
        check(file.isFile) { "Missing vision model. Copy vision_v1.pte to the app's models folder." }
        Module.load(file.absolutePath)
    }
    private var activeModule: Module? = null
    val inputShape = listOf(1, 3, height, width)

    override suspend fun analyze(bitmap: Bitmap): VisionResult = withContext(Dispatchers.Default) {
        val imageId = UUID.randomUUID().toString()
        val pixels = modelPixels(bitmap)
        val quality = assessQuality(pixels)
        if (!quality.ok) {
            return@withContext VisionResult(
                imageId = imageId, modelVersion = modelVersion, quality = quality,
                unknown = false, crop = "unknown",
            )
        }

        val logits = logits(normalize(pixels))
        val maxLogit = logits.max()
        val scores = logits.map { exp(((it - maxLogit) / temperature).toDouble()) }
        val sum = scores.sum()
        val ranked = scores.indices.sortedByDescending { scores[it] }
        val top = ranked.first()
        val unknown = labels[top] == "unknown" || scores[top] / sum < threshold
        val predictions = ranked.filter { labels[it] != "unknown" }.take(3).map { index ->
            val label = labels[index]
            val type = when {
                label.endsWith("__healthy") -> "healthy"
                label.startsWith("pest__") -> "pest"
                else -> "disease"
            }
            Prediction(label, type, (scores[index] / sum).toFloat())
        }
        val severity = if (unknown) null else when (predictions.first().type) {
            "healthy" -> SeverityInfo(0f, "none")
            "disease" -> estimateSeverity(pixels)
            else -> null
        }
        VisionResult(
            imageId = imageId, modelVersion = modelVersion, quality = quality, unknown = unknown,
            crop = if (unknown) "unknown" else labels[top].substringBefore("__"),
            predictions = predictions, severity = severity,
        )
    }

    fun logits(bitmap: Bitmap): FloatArray = logits(normalize(modelPixels(bitmap)))

    fun logits(input: FloatArray): FloatArray {
        require(input.size == 3 * width * height)
        val runtime = module.also { activeModule = it }
        val tensor = Tensor.fromBlob(input, inputShape.map(Int::toLong).toLongArray())
        return runtime.forward(EValue.from(tensor)).single().toTensor().dataAsFloatArray.also { output ->
            check(output.size == labels.size && output.all(Float::isFinite)) {
                "Vision model returned invalid scores."
            }
        }
    }

    private fun modelPixels(bitmap: Bitmap): IntArray {
        val scaled = Bitmap.createScaledBitmap(bitmap, width, height, true)
        return try {
            IntArray(width * height).also { scaled.getPixels(it, 0, width, 0, 0, width, height) }
        } finally {
            if (scaled !== bitmap) scaled.recycle()
        }
    }

    private fun normalize(pixels: IntArray): FloatArray {
        val values = FloatArray(pixels.size * 3)
        pixels.forEachIndexed { index, pixel ->
            values[index] = (Color.red(pixel) / 255f - mean[0]) / std[0]
            values[index + pixels.size] = (Color.green(pixel) / 255f - mean[1]) / std[1]
            values[index + 2 * pixels.size] = (Color.blue(pixel) / 255f - mean[2]) / std[2]
        }
        return values
    }

    private fun assessQuality(pixels: IntArray): QualityInfo {
        val gray = FloatArray(pixels.size)
        val hsv = FloatArray(3)
        var leafPixels = 0
        pixels.forEachIndexed { index, pixel ->
            gray[index] = Color.red(pixel) * 0.299f + Color.green(pixel) * 0.587f + Color.blue(pixel) * 0.114f
            Color.colorToHSV(pixel, hsv)
            val (hue, saturation, brightness) = hsv
            if ((hue in 40f..180f && saturation >= 25f / 255 && brightness >= 25f / 255) ||
                (hue in 20f..50f && saturation >= 40f / 255 && brightness in 30f / 255..200f / 255)
            ) {
                leafPixels++
            }
        }
        var total = 0.0
        var squares = 0.0
        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                val index = y * width + x
                val laplacian = gray[index - width] + gray[index + width] +
                    gray[index - 1] + gray[index + 1] - 4 * gray[index]
                total += laplacian
                squares += laplacian * laplacian
            }
        }
        val interior = (width - 2) * (height - 2)
        val blur = squares / interior - (total / interior) * (total / interior)
        val brightness = gray.average()
        val issues = buildList {
            if (blur < 100) add("blurry")
            if (brightness < 40) add("too_dark")
            if (brightness > 220) add("too_bright")
            if (leafPixels < pixels.size * 0.05) add("no_leaf")
        }
        return QualityInfo(issues.isEmpty(), issues)
    }

    // HSV heuristic from vision/severity.py. Camera estimates require field calibration.
    private fun estimateSeverity(pixels: IntArray): SeverityInfo? {
        val hsv = FloatArray(3)
        var leaf = 0
        var lesion = 0
        for (pixel in pixels) {
            Color.colorToHSV(pixel, hsv)
            val (hue, saturation, brightness) = hsv
            if (hue !in 10f..190f || saturation < 20f / 255 || brightness < 20f / 255) continue
            leaf++
            if (brightness < 100f / 255 || (hue <= 36 && saturation >= 30f / 255) ||
                ((hue < 56 || hue > 176) && saturation > 50f / 255)
            ) {
                lesion++
            }
        }
        if (leaf == 0) return null
        val percent = round(1000f * lesion / leaf) / 10f
        val band = when {
            percent <= 0.05 -> "none"
            percent <= 10 -> "mild"
            percent <= 30 -> "moderate"
            else -> "severe"
        }
        return SeverityInfo(percent, band)
    }

    override fun close() {
        activeModule?.destroy()
        activeModule = null
    }
}
