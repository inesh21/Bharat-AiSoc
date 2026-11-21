package com.offlinecrop.assistant.engine.executorch

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.BatteryManager
import android.os.SystemClock
import android.util.Log
import com.offlinecrop.assistant.engine.AdvisoryRequest
import com.offlinecrop.assistant.engine.Prediction
import com.offlinecrop.assistant.engine.QualityInfo
import com.offlinecrop.assistant.engine.SeverityInfo
import com.offlinecrop.assistant.engine.VisionResult
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.ZipFile
import kotlin.math.abs

private const val VECTOR_COUNT = 50
private const val BENCHMARK_COUNT = 10

internal suspend fun runDeviceSelfTest(
    context: Context,
    modelDir: File,
    progress: suspend (String) -> Unit,
): String {
    val reportDir = checkNotNull(context.getExternalFilesDir(null))
    val report = File(reportDir, "self-test.csv")
    val bundle = File(reportDir, "device_vectors.zip")
    check(bundle.isFile) { "Copy device_vectors.zip into the app's external files folder." }

    var tensorPasses = 0
    var imagePasses = 0
    var generationPasses = 0
    var safetyPasses = 0
    var benchmarks = 0
    var maxTensorError = 0f
    var maxImageError = 0f
    val eligible = mutableListOf<String>()
    ZipFile(bundle).use { zip ->
        val manifest = zip.getInputStream(checkNotNull(zip.getEntry("device/expected.json")))
            .bufferedReader().use { JSONObject(it.readText()) }
        val cases = manifest.getJSONArray("cases")
        val tolerance = manifest.getDouble("tolerance")
        check(cases.length() == VECTOR_COUNT && manifest.getInt("n_cases") == VECTOR_COUNT)
        check(tolerance.isFinite() && tolerance > 0)
        val temporary = File(reportDir, "self-test.csv.tmp")
        temporary.bufferedWriter().use { csv ->
            csv.appendLine("suite,case,language,status,vision_ms,ttft_wall_ms,decode_tokens_per_sec,total_ms,peak_rss_kib,battery_pct,battery_temp_c,tensor_error,image_error,token_callbacks")
            ExecuTorchVisionEngine(modelDir).use { vision ->
                val shape = manifest.getJSONArray("shape")
                check(vision.inputShape == List(shape.length()) { shape.getInt(it) })
                val tensorSize = vision.inputShape.reduce(Int::times)
                for (index in 0 until cases.length()) {
                    currentCoroutineContext().ensureActive()
                    val case = cases.getJSONObject(index)
                    check(case.getInt("test_id") == index)
                    val expected = case.getJSONArray("pt_logits")
                    val expectedTop = case.getInt("et_top1_idx")
                    val bytes = ByteArray(tensorSize * Float.SIZE_BYTES)
                    java.io.DataInputStream(zip.getInputStream(
                        checkNotNull(zip.getEntry("device/" + case.getString("input_bin"))),
                    )).use {
                        it.readFully(bytes)
                        check(it.read() == -1)
                    }
                    val tensor = FloatArray(tensorSize)
                    ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(tensor)
                    val started = SystemClock.elapsedRealtime()
                    val tensorOutput = vision.logits(tensor)
                    val visionMs = SystemClock.elapsedRealtime() - started
                    val tensorError = maxError(tensorOutput, expected)
                    maxTensorError = maxOf(maxTensorError, tensorError)
                    val tensorPass = topMatches(tensorOutput, expectedTop) && tensorError <= tolerance
                    if (tensorPass) tensorPasses++
                    val name = case.getString("image")
                    val image = zip.decode(name)
                    val imageOutput = try {
                        val output = vision.logits(image)
                        if (vision.analyze(image).let { it.quality.ok && !it.unknown }) eligible.add(name)
                        output
                    } finally {
                        image.recycle()
                    }
                    val imageError = maxError(imageOutput, expected)
                    maxImageError = maxOf(maxImageError, imageError)
                    val imagePass = topMatches(imageOutput, expectedTop) && imageError <= tolerance
                    if (imagePass) imagePasses++
                    val status = if (tensorPass && imagePass) "PASS" else "FAIL"
                    csv.appendLine("vision,$index,,$status,$visionMs,,,,,,,$tensorError,$imageError,")
                    progress("Vision " + (index + 1) + " / " + cases.length())
                }
            }

            val fixtures = context.assets.open("demo_ipm.json").bufferedReader()
                .use { JSONObject(it.readText()) }.keys().asSequence()
                .filterNot { it.endsWith("__healthy") || it.startsWith("pest__") }
                .sorted().take(10).toList()
            check(fixtures.size == 10)
            ExecuTorchAdvisoryEngine(context, modelDir).use { advisory ->
                var number = 0
                for (language in listOf("en", "hi", "te")) {
                    for (condition in fixtures) {
                        currentCoroutineContext().ensureActive()
                        val request = fixture(condition, language)
                        val response = advisory.advise(request) {}
                        val metrics = advisory.lastGeneration
                        val valid = metrics?.accepted == true && metrics.callbacks > 0 &&
                            response.status == "final" && response.language == language &&
                            response.sourceIds == listOf("kb:$condition") &&
                            response.actionsNow.isNotEmpty() && response.prevention.isNotEmpty() &&
                            !response.usedFallback
                        if (valid) generationPasses++
                        csv.appendLine(benchmarkRow("advisory", condition, language,
                            if (valid) "PASS" else "FAIL", null, metrics, metrics?.elapsedMs, context))
                        progress("Advisory " + ++number + " / 30")
                    }
                }
                val original = fixture(fixtures.first(), "en")
                val unknown = original.copy(vision = original.vision.copy(unknown = true))
                val poor = original.copy(vision = original.vision.copy(quality = QualityInfo(false, listOf("blurry"))))
                for ((name, request) in listOf("unknown" to unknown, "poor_quality" to poor)) {
                    val response = advisory.advise(request) {}
                    val passed = advisory.lastGeneration == null && response.seekHelp && response.actionsNow.isEmpty()
                    if (passed) safetyPasses++
                    csv.appendLine("safety,$name,en," + if (passed) "PASS" else "FAIL")
                }
                val invalid = listOf("""{"action":99}""", """{"action":0,"dose":"wrong"}""", "free text")
                for ((index, raw) in invalid.withIndex()) {
                    val passed = parseActionChoice(raw, 2) == null
                    if (passed) safetyPasses++
                    csv.appendLine("safety,invalid_output_$index,," + if (passed) "PASS" else "FAIL")
                }
            }

            val benchmarkInputs = if (eligible.isEmpty()) emptyList() else
                List(BENCHMARK_COUNT) { eligible[it % eligible.size] }
            for ((index, name) in benchmarkInputs.withIndex()) {
                currentCoroutineContext().ensureActive()
                val start = SystemClock.elapsedRealtime()
                val bitmap = zip.decode(name)
                val vision = try {
                    ExecuTorchVisionEngine(modelDir).use { it.analyze(bitmap) }
                } finally {
                    bitmap.recycle()
                }
                val visionMs = SystemClock.elapsedRealtime() - start
                ExecuTorchAdvisoryEngine(context, modelDir).use { advisory ->
                    val result = advisory.advise(AdvisoryRequest(vision = vision)) {}
                    val metrics = advisory.lastGeneration
                    val status = when {
                        result.usedFallback -> "FALLBACK"
                        result.status == "needs_clarification" -> "CLARIFICATION"
                        else -> "PASS"
                    }
                    csv.appendLine(benchmarkRow("pipeline", name, "en", status,
                        visionMs, metrics, SystemClock.elapsedRealtime() - start, context))
                }
                benchmarks++
                progress("Benchmarks " + (index + 1) + " / " + BENCHMARK_COUNT)
            }
        }
        check(temporary.renameTo(report)) { "Could not publish the self-test report." }
    }

    val summary = "Vision tensors $tensorPasses/50 (max error $maxTensorError), images $imagePasses/50 " +
        "(max error $maxImageError). Llama accepted $generationPasses/30. Safety $safetyPasses/5. " +
        "Pipeline benchmarks $benchmarks/$BENCHMARK_COUNT."
    Log.i("CropSelfTest", summary)
    return "$summary\n" + report.absolutePath
}

private fun maxError(output: FloatArray, expected: org.json.JSONArray): Float {
    check(output.size == expected.length())
    return output.indices.maxOf { abs(output[it] - expected.getDouble(it).toFloat()) }
}

private fun topMatches(output: FloatArray, expected: Int) =
    output.indices.maxByOrNull { output[it] } == expected

private fun ZipFile.decode(name: String): Bitmap =
    getInputStream(checkNotNull(getEntry("device/$name"))).use {
        checkNotNull(BitmapFactory.decodeStream(it))
    }

private fun fixture(condition: String, language: String) = AdvisoryRequest(
    vision = VisionResult(
        imageId = java.util.UUID.randomUUID().toString(),
        quality = QualityInfo(true),
        unknown = false,
        crop = condition.substringBefore("__"),
        predictions = listOf(Prediction(condition, "disease", 0.95f)),
        severity = SeverityInfo(18f, "moderate"),
    ),
    language = language,
)

private fun benchmarkRow(
    suite: String,
    name: String,
    language: String,
    status: String,
    visionMs: Long?,
    metrics: GenerationMetrics?,
    totalMs: Long?,
    context: Context,
): String {
    val battery = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    val scale = battery?.getIntExtra(BatteryManager.EXTRA_SCALE, -1)?.takeIf { it > 0 }
    val level = battery?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)?.takeIf { it >= 0 }
    val temperature = battery?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE)
        ?.takeUnless { it == Int.MIN_VALUE }?.div(10.0)
    val peak = runCatching {
        File("/proc/self/status").useLines { lines ->
            lines.firstOrNull { it.startsWith("VmHWM:") }
                ?.substringAfter(':')?.trim()?.substringBefore(' ')?.toLongOrNull()
        }
    }.getOrNull()
    return listOf(
        suite, name, language, status, visionMs, metrics?.wallTtftMs, metrics?.decodeTokensPerSecond,
        totalMs, peak, if (scale != null && level != null) level * 100 / scale else null,
        temperature, null, null, metrics?.callbacks,
    ).joinToString(",") { it?.toString().orEmpty() }
}
