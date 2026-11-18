package com.offlinecrop.assistant.engine.mock

import android.graphics.Bitmap
import com.offlinecrop.assistant.engine.*
import kotlinx.coroutines.delay
import java.util.UUID

/**
 * Mock implementation of VisionEngine allowing full UI development and verification (Task C4).
 * Returns realistic Contract 1 payloads covering diseases, pests, healthy leaves, and poor quality photos.
 */
class MockVisionEngine(
    var simulatedScenario: Scenario = Scenario.TOMATO_EARLY_BLIGHT
) : VisionEngine {

    enum class Scenario {
        TOMATO_EARLY_BLIGHT,
        POTATO_LATE_BLIGHT,
        RICE_BLAST,
        PEST_FALL_ARMYWORM,
        HEALTHY_LEAF,
        UNKNOWN_OOD,
        BLURRY_POOR_QUALITY
    }

    override suspend fun analyze(bitmap: Bitmap): VisionResult {
        // Simulate inference latency (e.g. 80ms - 150ms on mobile NPU/CPU)
        delay(120)

        val imageId = UUID.randomUUID().toString()

        return when (simulatedScenario) {
            Scenario.TOMATO_EARLY_BLIGHT -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = false,
                crop = "tomato",
                predictions = listOf(
                    Prediction("tomato__early_blight", "disease", 0.88f),
                    Prediction("tomato__septoria_leaf_spot", "disease", 0.08f),
                    Prediction("tomato__healthy", "healthy", 0.02f)
                ),
                severity = SeverityInfo(percent = 18.4f, band = "moderate")
            )

            Scenario.POTATO_LATE_BLIGHT -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = false,
                crop = "potato",
                predictions = listOf(
                    Prediction("potato__late_blight", "disease", 0.92f),
                    Prediction("potato__early_blight", "disease", 0.05f),
                    Prediction("potato__healthy", "healthy", 0.01f)
                ),
                severity = SeverityInfo(percent = 34.2f, band = "severe")
            )

            Scenario.RICE_BLAST -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = false,
                crop = "rice",
                predictions = listOf(
                    Prediction("rice__blast", "disease", 0.79f),
                    Prediction("rice__brown_spot", "disease", 0.16f),
                    Prediction("rice__healthy", "healthy", 0.03f)
                ),
                severity = SeverityInfo(percent = 8.5f, band = "mild")
            )

            Scenario.PEST_FALL_ARMYWORM -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = false,
                crop = "maize",
                predictions = listOf(
                    Prediction("pest__fall_armyworm", "pest", 0.84f),
                    Prediction("maize__common_rust", "disease", 0.09f),
                    Prediction("maize__healthy", "healthy", 0.04f)
                ),
                severity = null // Severity is null for pests per Contract 1
            )

            Scenario.HEALTHY_LEAF -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = false,
                crop = "tomato",
                predictions = listOf(
                    Prediction("tomato__healthy", "healthy", 0.96f),
                    Prediction("tomato__early_blight", "disease", 0.02f),
                    Prediction("tomato__bacterial_spot", "disease", 0.01f)
                ),
                severity = SeverityInfo(percent = 0.0f, band = "none")
            )

            Scenario.UNKNOWN_OOD -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = true, issues = emptyList()),
                unknown = true,
                crop = "unknown",
                predictions = listOf(
                    Prediction("unknown", "disease", 0.75f)
                ),
                severity = null
            )

            Scenario.BLURRY_POOR_QUALITY -> VisionResult(
                schemaVersion = "1.0",
                imageId = imageId,
                modelVersion = "vision_v1_mock",
                quality = QualityInfo(ok = false, issues = listOf("blurry", "too_dark")),
                unknown = true,
                crop = "unknown",
                predictions = emptyList(),
                severity = null
            )
        }
    }
}
