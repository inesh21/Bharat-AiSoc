package com.offlinecrop.assistant.engine.mock

import com.offlinecrop.assistant.engine.*
import kotlinx.coroutines.delay

/**
 * Mock implementation of AdvisoryEngine emitting Contract 3 responses (Task C4).
 * Demonstrates:
 * 1. Streamed token callbacks (onToken)
 * 2. Clarification loops when top two diagnoses are close
 * 3. Safe rules-grounded actions now, prevention, and fallback mechanisms
 */
class MockAdvisoryEngine : AdvisoryEngine {

    override fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse {
        val topPred = req.vision.predictions.firstOrNull()
        val lang = req.language

        // Check if clarifying question is required (e.g. if top-2 confidence difference < 0.15 and no answer yet)
        val secondPred = req.vision.predictions.getOrNull(1)
        val isAmbiguous = secondPred != null && (topPred != null && (topPred.confidence - secondPred.confidence) < 0.15f)
        val hasAnsweredClarification = req.answers.any { it.questionId == "q_underside_spots" }

        if (isAmbiguous && !hasAnsweredClarification) {
            return AdvisoryResponse(
                schemaVersion = "1.0",
                status = "needs_clarification",
                clarification = ClarificationQuestion(
                    questionId = "q_underside_spots",
                    text = when (lang) {
                        "hi" -> "क्या पत्तियों के नीचे की तरफ मखमली फफूंद या काले धब्बे दिखाई दे रहे हैं?"
                        "te" -> "ఆకుల కింద భాగాన బూజు లేదా నల్లటి మచ్చలు కనిపిస్తున్నాయా?"
                        else -> "Are there dark velvety spots or mould on the undersides of the leaves?"
                    },
                    options = listOf("yes", "no", "not_sure")
                ),
                diagnosis = "Possible ${topPred?.label ?: "infection"}",
                severityBand = req.vision.severity?.band ?: "moderate",
                actionsNow = emptyList(),
                prevention = emptyList(),
                seekHelp = false,
                sourceIds = listOf("kb:${topPred?.label ?: "rules"}"),
                usedFallback = false,
                language = lang,
                text = "Clarification needed."
            )
        }

        // Full advisory response
        val (diagnosisText, actions, preventionList, fullNarrative) = when (topPred?.label) {
            "tomato__early_blight" -> Quadruple(
                "Early Blight (Alternaria solani) on Tomato",
                listOf(
                    "Remove and destroy severely infected lower leaves immediately to stop spore spread.",
                    "Apply copper oxychloride (2.5 g/L water) or neem seed kernel extract (5%) thoroughly on both sides of leaves.",
                    "Avoid overhead irrigation; water at base of stems to keep foliage dry."
                ),
                listOf(
                    "Practice 3-year crop rotation avoiding Solanaceous crops (potato, brinjal).",
                    "Ensure adequate plant spacing (60 x 45 cm) for optimal aeration.",
                    "Mulch soil around plants with clean straw to prevent soil-splash pathogens."
                ),
                "Your tomato crop shows symptoms of Early Blight with moderate leaf damage. Prune lower diseased foliage immediately. Apply copper oxychloride spray ensuring safety gear is worn. Observe a 7-day pre-harvest interval."
            )

            "potato__late_blight" -> Quadruple(
                "Late Blight (Phytophthora infestans) on Potato",
                listOf(
                    "Destroy infected foliage immediately to protect tubers.",
                    "Apply Mancozeb (2 g/L) or Copper Hydroxide (2 g/L) preventative fungicide.",
                    "Hill up soil around stems to prevent spores washing into developing tubers."
                ),
                listOf(
                    "Plant certified disease-free seed tubers only.",
                    "Destroy volunteer potato and weed hosts near fields.",
                    "Ensure adequate field drainage to avoid water stagnation."
                ),
                "Severe Late Blight detected. Take immediate action as this pathogen spreads rapidly in cool, humid conditions. Spray approved protective fungicide promptly."
            )

            "rice__blast" -> Quadruple(
                "Rice Leaf Blast (Magnaporthe oryzae)",
                listOf(
                    "Avoid excess nitrogen fertilizer application which accelerates blast spread.",
                    "Maintain shallow standing water (2-3 cm) in fields.",
                    "Apply Tricyclazole 75% WP (0.6 g/L) upon early symptom appearance."
                ),
                listOf(
                    "Use blast-resistant seed varieties recommended by state agricultural university.",
                    "Treat seeds before sowing with carbendazim (2 g/kg seed).",
                    "Burn or compost infected straw residues after harvest."
                ),
                "Rice blast symptoms observed at mild severity. Regulate nitrogen top-dressing and apply recommended fungicide early in morning hours."
            )

            "pest__fall_armyworm" -> Quadruple(
                "Fall Armyworm (Spodoptera frugiperda) Infestation",
                listOf(
                    "Apply 5% Neem Seed Kernel Extract (NSKE) or Bacillus thuringiensis (Bt) formulation (2 g/L) into plant whorls.",
                    "Handpick egg masses and young caterpillars in small holdings.",
                    "Erect pheromone traps @ 5 per acre to monitor and trap adult moths."
                ),
                listOf(
                    "Intercrop maize with legume crops such as cowpea or desmodium.",
                    "Conserve natural predators such as predatory bugs and trichogramma wasps.",
                    "Synchronize planting dates with neighboring farms."
                ),
                "Fall Armyworm detected in crop whorls. Immediate bio-pesticide or recommended whorl application is advised to prevent inner leaf shredding."
            )

            "tomato__healthy", "potato__healthy", "rice__healthy", "maize__healthy", "cotton__healthy" -> Quadruple(
                "Healthy Leaf Tissue",
                listOf(
                    "No disease or pest damage detected. Continue standard agronomic practices.",
                    "Maintain balanced N-P-K fertilizer application as per growth stage."
                ),
                listOf(
                    "Inspect crops twice weekly for early pest/disease detection.",
                    "Maintain proper irrigation scheduling."
                ),
                "Good news! Your crop leaves appear healthy and robust with no detectable signs of blight, rust, or pest damage."
            )

            else -> Quadruple(
                "Condition Unknown / Inconclusive",
                listOf(
                    "Symptoms cannot be definitively identified from this photo.",
                    "Consult your local agricultural extension officer (KVK / Krishi Bhavan) with physical leaf specimen."
                ),
                listOf(
                    "Maintain general crop hygiene and clean field borders."
                ),
                "We could not definitively identify this condition offline. Please take a clearer photograph or consult an agricultural extension officer."
            )
        }

        // Simulate streaming tokens
        val tokens = fullNarrative.split(" ")
        for (tok in tokens) {
            onToken("$tok ")
        }

        return AdvisoryResponse(
            schemaVersion = "1.0",
            status = "final",
            clarification = null,
            diagnosis = diagnosisText,
            severityBand = req.vision.severity?.band ?: "moderate",
            actionsNow = actions,
            prevention = preventionList,
            seekHelp = topPred?.label == "unknown",
            sourceIds = listOf("kb:${topPred?.label ?: "rules"}"),
            usedFallback = false,
            language = lang,
            text = fullNarrative
        )
    }

    private data class Quadruple<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
}
