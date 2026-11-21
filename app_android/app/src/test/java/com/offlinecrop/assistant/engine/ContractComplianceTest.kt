package com.offlinecrop.assistant.engine

import com.offlinecrop.assistant.engine.mock.MockAdvisoryEngine
import com.offlinecrop.assistant.engine.mock.MockVisionEngine
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for Contract compliance and mock engine pipelines (Task C3, C4).
 */
class ContractComplianceTest {

    private lateinit var visionEngine: MockVisionEngine
    private lateinit var advisoryEngine: MockAdvisoryEngine

    @Before
    fun setUp() {
        visionEngine = MockVisionEngine()
        advisoryEngine = MockAdvisoryEngine()
    }

    @Test
    fun testContract1VisionResultStructure() = runBlocking {
        visionEngine.simulatedScenario = MockVisionEngine.Scenario.TOMATO_EARLY_BLIGHT
        val dummyBitmap = org.mockito.Mockito.mock(android.graphics.Bitmap::class.java)
        val result = visionEngine.analyze(dummyBitmap)

        assertEquals("1.0", result.schemaVersion)
        assertTrue(result.quality.ok)
        assertFalse(result.unknown)
        assertEquals("tomato", result.crop)
        assertTrue(result.predictions.isNotEmpty())
        assertEquals("tomato__early_blight", result.predictions[0].label)
        assertNotNull(result.severity)
        assertEquals("moderate", result.severity?.band)
    }

    @Test
    fun testContract1QualityIssueFlow() = runBlocking {
        visionEngine.simulatedScenario = MockVisionEngine.Scenario.BLURRY_POOR_QUALITY
        val dummyBitmap = org.mockito.Mockito.mock(android.graphics.Bitmap::class.java)
        val result = visionEngine.analyze(dummyBitmap)

        assertFalse(result.quality.ok)
        assertTrue(result.unknown)
        assertTrue(result.quality.issues.contains("blurry"))
        assertTrue(result.predictions.isEmpty())
        assertNull(result.severity)
    }

    @Test
    fun testContract2And3AdvisoryClarificationLoop() {
        val ambiguousVision = VisionResult(
            imageId = "test_ambiguous",
            quality = QualityInfo(ok = true),
            unknown = false,
            crop = "tomato",
            predictions = listOf(
                Prediction("tomato__early_blight", "disease", 0.52f),
                Prediction("tomato__septoria_leaf_spot", "disease", 0.48f)
            ),
            severity = SeverityInfo(percent = 15f, band = "moderate")
        )

        val req1 = AdvisoryRequest(vision = ambiguousVision, language = "en")
        val response1 = advisoryEngine.advise(req1) {}

        // Ambiguous prediction should trigger clarification loop
        assertEquals("needs_clarification", response1.status)
        assertNotNull(response1.clarification)
        assertEquals("q_underside_spots", response1.clarification?.questionId)

        // Farmer answers clarification
        val req2 = AdvisoryRequest(
            vision = ambiguousVision,
            language = "en",
            answers = listOf(ClarificationAnswer("q_underside_spots", "yes"))
        )
        val response2 = advisoryEngine.advise(req2) {}
        assertEquals("final", response2.status)
        assertTrue(response2.actionsNow.isNotEmpty())
        assertTrue(response2.prevention.isNotEmpty())
    }
}
