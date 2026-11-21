package com.offlinecrop.assistant

import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.offlinecrop.assistant.engine.AdvisoryRequest
import com.offlinecrop.assistant.engine.AdvisoryResponse
import com.offlinecrop.assistant.engine.ClarificationAnswer
import com.offlinecrop.assistant.engine.VisionResult
import com.offlinecrop.assistant.engine.decodePhoto
import com.offlinecrop.assistant.engine.executorch.ExecuTorchAdvisoryEngine
import com.offlinecrop.assistant.engine.executorch.ExecuTorchVisionEngine
import com.offlinecrop.assistant.engine.executorch.runDeviceSelfTest
import com.offlinecrop.assistant.engine.mock.MockAdvisoryEngine
import com.offlinecrop.assistant.engine.mock.MockVisionEngine
import com.offlinecrop.assistant.engine.speech.AndroidSpeechEngine
import com.offlinecrop.assistant.ui.screens.AdvisoryScreen
import com.offlinecrop.assistant.ui.screens.CameraScreen
import com.offlinecrop.assistant.ui.screens.LanguageScreen
import com.offlinecrop.assistant.ui.screens.LiveCameraScreen
import com.offlinecrop.assistant.ui.screens.ResultScreen
import com.offlinecrop.assistant.ui.screens.Screen
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class MainActivity : ComponentActivity() {
    private lateinit var speech: AndroidSpeechEngine
    private val mockVision by lazy { MockVisionEngine() }
    private val mockAdvisory by lazy { MockAdvisoryEngine() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        speech = AndroidSpeechEngine(this)
        setContent {
            MaterialTheme {
                Surface(Modifier.fillMaxSize().systemBarsPadding()) {
                    AppContent()
                }
            }
        }
    }

    override fun onStop() {
        speech.stopSpeaking()
        super.onStop()
    }

    override fun onDestroy() {
        speech.shutdown()
        super.onDestroy()
    }

    private fun modelDir(): File = checkNotNull(getExternalFilesDir("models")) {
        "The app's model folder is unavailable."
    }

    @Composable
    private fun AppContent() {
        val nav = rememberNavController()
        var language by rememberSaveable { mutableStateOf("en") }
        var vision by remember { mutableStateOf<VisionResult?>(null) }
        var advisory by remember { mutableStateOf<AdvisoryResponse?>(null) }
        var busy by remember { mutableStateOf(false) }
        var progress by remember { mutableStateOf("") }
        var error by remember { mutableStateOf<String?>(null) }
        var speaking by remember { mutableStateOf(false) }
        var report by remember { mutableStateOf<String?>(null) }
        val selfTestRoute = "self_test"
        DisposableEffect(Unit) {
            speech.observeStatus { playing, message ->
                speaking = playing
                if (message != null) error = message
            }
            onDispose { speech.observeStatus { _, _ -> } }
        }

        fun runTask(label: String, task: suspend () -> Unit) {
            if (busy) return
            busy = true
            progress = label
            error = null
            lifecycleScope.launch {
                try {
                    task()
                } catch (e: CancellationException) {
                    throw e
                } catch (e: OutOfMemoryError) {
                    Log.e("CropAssistant", label, e)
                    error = "The phone ran out of memory. Close other apps and retry."
                } catch (e: Exception) {
                    Log.e("CropAssistant", label, e)
                    error = e.message ?: "Operation failed. Please try again."
                } finally {
                    busy = false
                }
            }
        }

        fun analyzePhoto(uri: Uri, temporary: File?) {
            if (isDestroyed || busy || nav.currentDestination?.route != Screen.Camera.route) {
                temporary?.delete()
                return
            }
            runTask("Analyzing photo") {
                try {
                    vision = withContext(Dispatchers.IO) {
                        val bitmap = decodePhoto(contentResolver, uri)
                        try {
                            ExecuTorchVisionEngine(modelDir()).use { it.analyze(bitmap) }
                        } finally {
                            bitmap.recycle()
                        }
                    }
                } finally {
                    temporary?.delete()
                }
                advisory = null
                nav.navigate(Screen.Result.route)
            }
        }

        fun requestAdvisory(answer: ClarificationAnswer? = null) {
            val result = vision ?: return
            if (!result.quality.ok || result.unknown || result.predictions.isEmpty()) return
            speech.stopSpeaking()
            val request = AdvisoryRequest(
                vision = result, language = language, answers = listOfNotNull(answer),
            )
            runTask("Preparing advisory") {
                advisory = withContext(Dispatchers.Default) {
                    if (BuildConfig.USE_MOCKS) {
                        mockAdvisory.advise(request) {}
                    } else {
                        ExecuTorchAdvisoryEngine(this@MainActivity, modelDir()).use {
                            it.advise(request) {}
                        }
                    }
                }
                if (nav.currentDestination?.route != Screen.Advisory.route) {
                    nav.navigate(Screen.Advisory.route)
                }
            }
        }

        fun retake() {
            if (busy) return
            speech.stopSpeaking()
            error = null
            vision = null
            advisory = null
            if (!nav.popBackStack(Screen.Camera.route, false)) {
                nav.navigate(Screen.Camera.route) { launchSingleTop = true }
            }
        }

        BackHandler(busy) {}
        Column(Modifier.fillMaxSize()) {
            if (busy) {
                LinearProgressIndicator(Modifier.fillMaxWidth())
                Text(progress, Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
            }
            error?.let {
                Text(it, Modifier.padding(16.dp), color = MaterialTheme.colorScheme.error)
            }
            NavHost(nav, startDestination = Screen.Language.route, modifier = Modifier.weight(1f)) {
                composable(Screen.Language.route) {
                    LanguageScreen(
                        currentLanguage = language,
                        onLanguageSelected = { language = it },
                        onNavigateNext = {
                            error = null
                            nav.navigate(Screen.Camera.route)
                        },
                        onSelfTest = if (BuildConfig.USE_MOCKS) null else {
                            { error = null; nav.navigate(selfTestRoute) }
                        },
                    )
                }
                composable(Screen.Camera.route) {
                    if (BuildConfig.USE_MOCKS) {
                        CameraScreen(
                            onSimulateScan = { scenario ->
                                runTask("Analyzing test image") {
                                    mockVision.simulatedScenario = scenario
                                    val bitmap = Bitmap.createBitmap(1, 1, Bitmap.Config.ARGB_8888)
                                    try {
                                        vision = mockVision.analyze(bitmap)
                                    } finally {
                                        bitmap.recycle()
                                    }
                                    nav.navigate(Screen.Result.route)
                                }
                            },
                            onNavigateHistory = {},
                        )
                    } else {
                        LiveCameraScreen(busy, ::analyzePhoto)
                    }
                }
                composable(Screen.Result.route) {
                    ResultScreen(vision, { requestAdvisory() }, ::retake)
                }
                composable(Screen.Advisory.route) {
                    DisposableEffect(Unit) { onDispose { speech.stopSpeaking() } }
                    AdvisoryScreen(
                        advisoryResponse = advisory,
                        onSpeak = { if (!busy) speech.speak(it, language) },
                        onStopSpeak = speech::stopSpeaking,
                        isSpeaking = speaking,
                        onAnswerClarification = { answer ->
                            advisory?.clarification?.let {
                                requestAdvisory(ClarificationAnswer(it.questionId, answer))
                            }
                        },
                        onFinish = ::retake,
                    )
                }
                composable(selfTestRoute) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("Device self-test", style = MaterialTheme.typography.headlineSmall)
                        Text("Runs vision parity, Llama generation, safety checks and device benchmarks.")
                        Button(enabled = !busy, onClick = {
                            report = null
                            val voices = speech.voiceAvailability().toString()
                            runTask("Starting device self-test") {
                                val result = withContext(Dispatchers.Default) {
                                    runDeviceSelfTest(this@MainActivity, modelDir()) { step ->
                                        withContext(Dispatchers.Main) { progress = step }
                                    }
                                }
                                report = "$result\nOffline voices $voices"
                                Log.i("CropSelfTest", "Offline voices $voices")
                            }
                        }) {
                            Text("Run checks")
                        }
                        report?.let { Text(it) }
                    }
                }
            }
        }
    }
}
