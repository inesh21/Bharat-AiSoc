package com.offlinecrop.assistant

import android.os.Bundle
import android.util.Log
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
import com.offlinecrop.assistant.engine.executorch.ExecuTorchAdvisoryEngine
import com.offlinecrop.assistant.engine.executorch.ExecuTorchVisionEngine
import com.offlinecrop.assistant.engine.mock.MockAdvisoryEngine
import com.offlinecrop.assistant.engine.mock.MockVisionEngine
import com.offlinecrop.assistant.engine.speech.AndroidSpeechEngine
import com.offlinecrop.assistant.ui.screens.*
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var visionEngine: VisionEngine
    private lateinit var advisoryEngine: AdvisoryEngine
    private lateinit var speechEngine: AndroidSpeechEngine

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Get model directory (app's external files dir)
        val modelDir = getExternalFilesDir("models") ?: throw IllegalStateException("External files dir not available")

        // Initialize engines based on build config
        visionEngine = if (BuildConfig.USE_MOCKS) {
            Log.i("MainActivity", "⚠️ MOCK MODE - Using mock vision engine")
            MockVisionEngine()
        } else {
            Log.i("MainActivity", "Using REAL ExecuTorch vision engine from $modelDir")
            try {
                ExecuTorchVisionEngine(this, modelDir)
            } catch (e: Exception) {
                Log.e("MainActivity", "❌ Failed to load ExecuTorch vision: ${e.message}", e)
                throw RuntimeException("Vision model load failed. Check logcat and ensure models are pushed.", e)
            }
        }

        advisoryEngine = if (BuildConfig.USE_MOCKS) {
            Log.i("MainActivity", "⚠️ MOCK MODE - Using mock advisory engine")
            MockAdvisoryEngine()
        } else {
            Log.i("MainActivity", "Using REAL ExecuTorch advisory engine from $modelDir")
            try {
                ExecuTorchAdvisoryEngine(this, modelDir)
            } catch (e: Exception) {
                Log.e("MainActivity", "❌ Failed to load ExecuTorch advisory: ${e.message}", e)
                throw RuntimeException("Advisory model load failed. Check logcat and ensure models are pushed.", e)
            }
        }

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
                                    // For mock engines only
                                    if (visionEngine is MockVisionEngine) {
                                        (visionEngine as MockVisionEngine).simulatedScenario = scenario
                                    }
                                    lifecycleScope.launch {
                                        // Bitmap placeholder for mock analysis
                                        val dummyBitmap = android.graphics.Bitmap.createBitmap(224, 224, android.graphics.Bitmap.Config.ARGB_8888)
                                        val result = visionEngine.analyze(dummyBitmap)
                                        currentVisionResult = result

                                        // Handle quality issues
                                        if (!result.quality.ok) {
                                            Log.w("MainActivity", "Image quality issues: ${result.quality.issues}")
                                            // Show quality issues and allow retake
                                            navController.navigate(Screen.Result.route)
                                        } else if (result.unknown) {
                                            Log.w("MainActivity", "Unknown/OOD detection")
                                            navController.navigate(Screen.Result.route)
                                        } else {
                                            navController.navigate(Screen.Result.route)
                                        }
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
                                    val questionId = currentAdvisoryResponse?.clarification?.questionId ?: ""
                                    if (vis != null) {
                                        val req = AdvisoryRequest(
                                            vision = vis,
                                            language = selectedLanguage,
                                            answers = listOf(ClarificationAnswer(questionId, answer))
                                        )
                                        lifecycleScope.launch {
                                            val updatedAdv = advisoryEngine.advise(req) { token ->
                                                // Token streaming callback - UI will update automatically
                                            }
                                            currentAdvisoryResponse = updatedAdv

                                            // Handle validation failures
                                            if (updatedAdv.usedFallback) {
                                                Log.w("MainActivity", "Advisory validation failed, using fallback")
                                            }
                                        }
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

        // Release ExecuTorch resources
        if (visionEngine is ExecuTorchVisionEngine) {
            (visionEngine as ExecuTorchVisionEngine).release()
        }
        if (advisoryEngine is ExecuTorchAdvisoryEngine) {
            (advisoryEngine as ExecuTorchAdvisoryEngine).release()
        }

        speechEngine.shutdown()
    }
}
