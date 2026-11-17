package com.offlinecrop.assistant

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.offlinecrop.assistant.engine.*
import com.offlinecrop.assistant.engine.mock.MockAdvisoryEngine
import com.offlinecrop.assistant.engine.mock.MockVisionEngine
import com.offlinecrop.assistant.engine.speech.AndroidSpeechEngine
import com.offlinecrop.assistant.ui.screens.*
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var visionEngine: MockVisionEngine
    private lateinit var advisoryEngine: MockAdvisoryEngine
    private lateinit var speechEngine: AndroidSpeechEngine

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        visionEngine = MockVisionEngine()
        advisoryEngine = MockAdvisoryEngine()
        speechEngine = AndroidSpeechEngine(this)

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()

                    var selectedLanguage by remember { mutableStateOf("en") }
                    var currentVisionResult by remember { mutableStateOf<VisionResult?>(null) }
                    var currentAdvisoryResponse by remember { mutableStateOf<AdvisoryResponse?>(null) }
                    var isSpeaking by remember { mutableStateOf(false) }

                    NavHost(navController = navController, startDestination = Screen.Language.route) {
                        // 1. Language Screen
                        composable(Screen.Language.route) {
                            LanguageScreen(
                                currentLanguage = selectedLanguage,
                                onLanguageSelected = { selectedLanguage = it },
                                onNavigateNext = { navController.navigate(Screen.Camera.route) }
                            )
                        }

                        // 2. Camera Screen
                        composable(Screen.Camera.route) {
                            CameraScreen(
                                onSimulateScan = { scenario ->
                                    visionEngine.simulatedScenario = scenario
                                    lifecycleScope.launch {
                                        // Bitmap placeholder for mock analysis
                                        val dummyBitmap = android.graphics.Bitmap.createBitmap(224, 224, android.graphics.Bitmap.Config.ARGB_8888)
                                        val result = visionEngine.analyze(dummyBitmap)
                                        currentVisionResult = result
                                        navController.navigate(Screen.Result.route)
                                    }
                                },
                                onNavigateHistory = { /* Open history */ }
                            )
                        }

                        // 3. Result Screen
                        composable(Screen.Result.route) {
                            ResultScreen(
                                visionResult = currentVisionResult,
                                onProceedAdvisory = {
                                    val vis = currentVisionResult
                                    if (vis != null) {
                                        val req = AdvisoryRequest(
                                            vision = vis,
                                            language = selectedLanguage
                                        )
                                        val adv = advisoryEngine.advise(req) {}
                                        currentAdvisoryResponse = adv
                                        navController.navigate(Screen.Advisory.route)
                                    }
                                },
                                onRetake = {
                                    navController.popBackStack(Screen.Camera.route, inclusive = false)
                                }
                            )
                        }

                        // 4. Advisory Screen
                        composable(Screen.Advisory.route) {
                            AdvisoryScreen(
                                advisoryResponse = currentAdvisoryResponse,
                                onSpeak = { text ->
                                    speechEngine.speak(text, selectedLanguage)
                                    isSpeaking = true
                                },
                                onStopSpeak = {
                                    speechEngine.stopSpeaking()
                                    isSpeaking = false
                                },
                                isSpeaking = isSpeaking,
                                onAnswerClarification = { answer ->
                                    val vis = currentVisionResult
                                    if (vis != null) {
                                        val req = AdvisoryRequest(
                                            vision = vis,
                                            language = selectedLanguage,
                                            answers = listOf(ClarificationAnswer("q_underside_spots", answer))
                                        )
                                        val updatedAdv = advisoryEngine.advise(req) {}
                                        currentAdvisoryResponse = updatedAdv
                                    }
                                },
                                onFinish = {
                                    speechEngine.stopSpeaking()
                                    isSpeaking = false
                                    navController.navigate(Screen.Camera.route) {
                                        popUpTo(Screen.Camera.route) { inclusive = true }
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        speechEngine.shutdown()
    }
}
