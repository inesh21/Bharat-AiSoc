package com.offlinecrop.assistant

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : ComponentActivity() {

    private var visionEngine: VisionEngine? = null
    private var advisoryEngine: AdvisoryEngine? = null
    private lateinit var speechEngine: AndroidSpeechEngine

    private var loadError: String? = null
    private var isLoading = true

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        speechEngine = AndroidSpeechEngine(this)

        // Load models off main thread
        lifecycleScope.launch(Dispatchers.IO) {
            loadModels()
        }

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    if (isLoading) {
                        LoadingScreen()
                    } else if (loadError != null) {
                        ErrorScreen(loadError!!)
                    } else {
                        AppContent()
                    }
                }
            }
        }
    }

    private suspend fun loadModels() {
        try {
            val modelDir = getExternalFilesDir("models")
            if (modelDir == null) {
                loadError = "External files directory not available"
                isLoading = false
                return
            }

            if (BuildConfig.USE_MOCKS) {
                Log.i("ET", "⚠️ MOCK MODE - Using mock engines")
                visionEngine = MockVisionEngine()
                advisoryEngine = MockAdvisoryEngine()
                isLoading = false
                return
            }

            // Load Vision Model
            val visionFile = File(modelDir, "vision_v1.pte")
            val visionJsonFile = File(modelDir, "vision_v1.json")

            Log.i("ET", "Vision model path: ${visionFile.absolutePath}")
            Log.i("ET", "Vision model exists: ${visionFile.exists()}, length: ${if (visionFile.exists()) visionFile.length() else 0}")
            Log.i("ET", "Vision JSON exists: ${visionJsonFile.exists()}, length: ${if (visionJsonFile.exists()) visionJsonFile.length() else 0}")

            try {
                visionEngine = ExecuTorchVisionEngine(this@MainActivity, modelDir)
                Log.i("ET", "✓ Vision engine loaded successfully")
            } catch (t: Throwable) {
                val msg = "Vision load failed for ${visionFile.absolutePath}: ${t.javaClass.name}: ${t.message}"
                Log.e("ET", msg, t)
                loadError = msg
                isLoading = false
                return
            }

            // Load LLM Model
            val llmFile = File(modelDir, "llama32_1b.pte")
            val tokenizerFile = File(modelDir, "tokenizer.model")

            Log.i("ET", "LLM model path: ${llmFile.absolutePath}")
            Log.i("ET", "LLM model exists: ${llmFile.exists()}, length: ${if (llmFile.exists()) llmFile.length() else 0}")
            Log.i("ET", "Tokenizer exists: ${tokenizerFile.exists()}, length: ${if (tokenizerFile.exists()) tokenizerFile.length() else 0}")

            try {
                advisoryEngine = ExecuTorchAdvisoryEngine(this@MainActivity, modelDir)
                Log.i("ET", "✓ Advisory engine loaded successfully")
            } catch (t: Throwable) {
                val msg = "LLM load failed for ${llmFile.absolutePath}: ${t.javaClass.name}: ${t.message}"
                Log.e("ET", msg, t)
                loadError = msg
                isLoading = false
                return
            }

            isLoading = false
            Log.i("ET", "✓ All models loaded successfully")

        } catch (t: Throwable) {
            val msg = "Model loading failed: ${t.javaClass.name}: ${t.message}"
            Log.e("ET", msg, t)
            loadError = msg
            isLoading = false
        }
    }

    @Composable
    private fun LoadingScreen() {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(16.dp))
                Text("Loading models...")
            }
        }
    }

    @Composable
    private fun ErrorScreen(error: String) {
        Box(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "Model Load Failed",
                    style = MaterialTheme.typography.headlineMedium,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = error,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }

    @Composable
    private fun AppContent() {
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
                            val result = visionEngine!!.analyze(dummyBitmap)
                            currentVisionResult = result

                            // Handle quality issues
                            if (!result.quality.ok) {
                                Log.w("MainActivity", "Image quality issues: ${result.quality.issues}")
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
                        if (currentVisionResult != null && currentVisionResult!!.quality.ok && !currentVisionResult!!.unknown) {
                            lifecycleScope.launch {
                                val req = AdvisoryRequest(
                                    vision = currentVisionResult!!,
                                    language = selectedLanguage
                                )
                                val advisory = advisoryEngine!!.advise(req) { /* token callback */ }
                                currentAdvisoryResponse = advisory
                                navController.navigate(Screen.Advisory.route)
                            }
                        }
                    },
                    onRetake = { navController.navigate(Screen.Camera.route) }
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
                                val updatedAdv = advisoryEngine!!.advise(req) { /* token callback */ }
                                currentAdvisoryResponse = updatedAdv

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
