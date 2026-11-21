package com.offlinecrop.assistant.ui.screens

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.offlinecrop.assistant.engine.*
import com.offlinecrop.assistant.engine.mock.MockVisionEngine

// Navigation Destinations
sealed class Screen(val route: String) {
    object Language : Screen("language")
    object Camera : Screen("camera")
    object Result : Screen("result")
    object Advisory : Screen("advisory")
    object History : Screen("history")
}

// ----------------------------------------------------
// 1. LANGUAGE PICKER SCREEN (Task C5)
// ----------------------------------------------------
@Composable
fun LanguageScreen(
    currentLanguage: String,
    onLanguageSelected: (String) -> Unit,
    onNavigateNext: () -> Unit
) {
    val languages = listOf(
        Triple("English", "en", "English"),
        Triple("हिन्दी", "hi", "Hindi"),
        Triple("తెలుగు", "te", "Telugu"),
        Triple("தமிழ்", "ta", "Tamil"),
        Triple("ಕನ್ನಡ", "kn", "Kannada"),
        Triple("मराठी", "mr", "Marathi")
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.Eco,
            contentDescription = "App Logo",
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(72.dp)
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Offline Crop Assistant",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Select your language / अपनी भाषा चुनें",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(32.dp))

        languages.forEach { (name, code, desc) ->
            val isSelected = currentLanguage == code
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 6.dp)
                    .clickable {
                        onLanguageSelected(code)
                    },
                colors = CardDefaults.cardColors(
                    containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(text = name, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                        Text(text = desc, fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (isSelected) {
                        Icon(
                            imageVector = Icons.Default.CheckCircle,
                            contentDescription = "Selected",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
        Button(
            onClick = onNavigateNext,
            modifier = Modifier.fillMaxWidth().height(52.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text(text = "Proceed to Camera / आगे बढ़ें", fontSize = 16.sp)
        }
    }
}

// ----------------------------------------------------
// 2. CAMERA CAPTURE & FRAMING GUIDE SCREEN (Task C5, C6)
// ----------------------------------------------------
@Composable
fun CameraScreen(
    onSimulateScan: (MockVisionEngine.Scenario) -> Unit,
    onNavigateHistory: () -> Unit
) {
    var selectedScenario by remember { mutableStateOf(MockVisionEngine.Scenario.TOMATO_EARLY_BLIGHT) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Top app bar with history action
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = "Capture Leaf Photo", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            IconButton(onClick = onNavigateHistory) {
                Icon(imageVector = Icons.Default.History, contentDescription = "History")
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Framing guide box (represents camera preview frame)
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(Color.Black, shape = RoundedCornerShape(16.dp)),
            contentAlignment = Alignment.Center
        ) {
            // Viewfinder Guide Overlay
            Box(
                modifier = Modifier
                    .size(240.dp)
                    .background(Color.Transparent, shape = RoundedCornerShape(12.dp))
            ) {
                // Leaf outline placeholder
                Icon(
                    imageVector = Icons.Default.FilterVintage,
                    contentDescription = "Target Leaf",
                    tint = Color.White.copy(alpha = 0.5f),
                    modifier = Modifier.size(100.dp).align(Alignment.Center)
                )
            }

            // Quality guidelines pill
            Surface(
                modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 16.dp),
                color = Color.Black.copy(alpha = 0.7f),
                shape = RoundedCornerShape(20.dp)
            ) {
                Text(
                    text = "Fill box with single leaf • Keep in focus • Natural light",
                    color = Color.White,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Scenario selector for rapid testing & verification (Task C4)
        Text(text = "Simulate Scan Scenario (Offline Mocks):", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        Spacer(modifier = Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.TOMATO_EARLY_BLIGHT,
                onClick = { selectedScenario = MockVisionEngine.Scenario.TOMATO_EARLY_BLIGHT },
                label = { Text("Early Blight") }
            )
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.POTATO_LATE_BLIGHT,
                onClick = { selectedScenario = MockVisionEngine.Scenario.POTATO_LATE_BLIGHT },
                label = { Text("Late Blight") }
            )
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.PEST_FALL_ARMYWORM,
                onClick = { selectedScenario = MockVisionEngine.Scenario.PEST_FALL_ARMYWORM },
                label = { Text("Pest") }
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.HEALTHY_LEAF,
                onClick = { selectedScenario = MockVisionEngine.Scenario.HEALTHY_LEAF },
                label = { Text("Healthy") }
            )
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.UNKNOWN_OOD,
                onClick = { selectedScenario = MockVisionEngine.Scenario.UNKNOWN_OOD },
                label = { Text("Unknown OOD") }
            )
            FilterChip(
                selected = selectedScenario == MockVisionEngine.Scenario.BLURRY_POOR_QUALITY,
                onClick = { selectedScenario = MockVisionEngine.Scenario.BLURRY_POOR_QUALITY },
                label = { Text("Blurry") }
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Shutter Button
        Button(
            onClick = { onSimulateScan(selectedScenario) },
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
            shape = RoundedCornerShape(14.dp)
        ) {
            Icon(imageVector = Icons.Default.CameraAlt, contentDescription = "Capture")
            Spacer(modifier = Modifier.width(8.dp))
            Text("Analyze Leaf (Zero Internet)", fontSize = 16.sp, fontWeight = FontWeight.Bold)
        }
    }
}

// ----------------------------------------------------
// 3. RESULT CARD SCREEN (Contract 1 Vision Display)
// ----------------------------------------------------
@Composable
fun ResultScreen(
    visionResult: VisionResult?,
    onProceedAdvisory: () -> Unit,
    onRetake: () -> Unit
) {
    if (visionResult == null) {
        Column(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("No scan data available.")
            Button(onClick = onRetake) { Text("Back to Camera") }
        }
        return
    }

    val isQualityIssue = !visionResult.quality.ok
    val isUnknown = visionResult.unknown

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        item {
            Text(text = "Scan Results", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(16.dp))
        }

        // Quality Issue Warning
        if (isQualityIssue) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Warning, contentDescription = "Warning", tint = MaterialTheme.colorScheme.error)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = "Image Quality Issue Detected", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = "Detected issues: ${visionResult.quality.issues.joinToString(", ")}")
                        Text(text = "Please retake the photo in good lighting and ensure the leaf is clearly in focus.")
                    }
                }
            }
        }

        // Unknown / OOD Warning
        if (isUnknown && !isQualityIssue) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.HelpOutline, contentDescription = "Unknown", tint = MaterialTheme.colorScheme.tertiary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = "Uncertain / Unrecognized", fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = "This plant or symptom is not recognized with high confidence. To protect your crop, please consult an agricultural extension officer (KVK).")
                    }
                }
            }
        }

        // Predictions List
        item {
            Text(text = "Top Diagnoses (Calibrated)", fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth())
            Spacer(modifier = Modifier.height(8.dp))
        }

        items(visionResult.predictions) { pred ->
            val confidencePct = (pred.confidence * 100).toInt()
            Card(
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                shape = RoundedCornerShape(10.dp)
            ) {
                Row(
                    modifier = Modifier.padding(14.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(text = pred.label.replace("__", " - ").replace("_", " "), fontWeight = FontWeight.Bold)
                        Text(text = "Type: ${pred.type}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Surface(
                        color = MaterialTheme.colorScheme.primaryContainer,
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text(
                            text = "$confidencePct%",
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }
                }
            }
        }

        // Severity Card
        if (visionResult.severity != null) {
            item {
                Spacer(modifier = Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = when (visionResult.severity.band) {
                            "severe" -> MaterialTheme.colorScheme.errorContainer
                            "moderate" -> Color(0xFFFFECC8)
                            "mild" -> Color(0xFFE8F5E9)
                            else -> MaterialTheme.colorScheme.surfaceVariant
                        }
                    )
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp).fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(text = "Severity Grade", fontWeight = FontWeight.Bold)
                            Text(text = "Lesion Area: ${visionResult.severity.percent}%")
                        }
                        Text(
                            text = visionResult.severity.band.uppercase(),
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 18.sp
                        )
                    }
                }
            }
        }

        // Action Buttons
        item {
            Spacer(modifier = Modifier.height(24.dp))
            if (!isQualityIssue && !isUnknown) {
                Button(
                    onClick = onProceedAdvisory,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(imageVector = Icons.Default.Chat, contentDescription = "Advisory")
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "Get Treatment Advisory", fontSize = 16.sp)
                }
                Spacer(modifier = Modifier.height(12.dp))
            }

            OutlinedButton(
                onClick = onRetake,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(text = "Take Another Photo")
            }
        }
    }
}

// ----------------------------------------------------
// 4. ADVISORY & CLARIFICATION SCREEN (Contract 3 Display + Voice)
// ----------------------------------------------------
@Composable
fun AdvisoryScreen(
    advisoryResponse: AdvisoryResponse?,
    onSpeak: (String) -> Unit,
    onStopSpeak: () -> Unit,
    isSpeaking: Boolean,
    onAnswerClarification: (String) -> Unit,
    onFinish: () -> Unit
) {
    if (advisoryResponse == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Advisory Plan", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                // Voice button (Task C9)
                IconButton(onClick = {
                    if (isSpeaking) onStopSpeak() else onSpeak(advisoryResponse.text)
                }) {
                    Icon(
                        imageVector = if (isSpeaking) Icons.Default.VolumeOff else Icons.Default.VolumeUp,
                        contentDescription = "Voice Speech",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Clarifying Question Loop (Task C5 & Contract 3)
        if (advisoryResponse.status == "needs_clarification" && advisoryResponse.clarification != null) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.QuestionAnswer, contentDescription = "Question")
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = "Clarification Needed", fontWeight = FontWeight.Bold)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = advisoryResponse.clarification.text, fontSize = 16.sp)
                        Spacer(modifier = Modifier.height(16.dp))

                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                            Button(onClick = { onAnswerClarification("yes") }) { Text("Yes / हाँ") }
                            Button(onClick = { onAnswerClarification("no") }) { Text("No / नहीं") }
                            OutlinedButton(onClick = { onAnswerClarification("not_sure") }) { Text("Not Sure") }
                        }
                    }
                }
            }
        }

        // Final Advisory Card
        if (advisoryResponse.status == "final") {
            item {
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = "Diagnosis", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        Text(text = advisoryResponse.diagnosis, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = advisoryResponse.text, fontSize = 15.sp, lineHeight = 22.sp)
                    }
                }
            }

            // Actions Now
            if (advisoryResponse.actionsNow.isNotEmpty()) {
                item {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(text = "Immediate Actions (Organic & Safe Chemical)", fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth())
                    Spacer(modifier = Modifier.height(6.dp))
                }
                items(advisoryResponse.actionsNow) { action ->
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(modifier = Modifier.padding(12.dp)) {
                            Icon(imageVector = Icons.Default.Check, contentDescription = "Action", tint = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = action, fontSize = 14.sp)
                        }
                    }
                }
            }

            // Prevention
            if (advisoryResponse.prevention.isNotEmpty()) {
                item {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(text = "Long-Term Prevention", fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth())
                    Spacer(modifier = Modifier.height(6.dp))
                }
                items(advisoryResponse.prevention) { prev ->
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(modifier = Modifier.padding(12.dp)) {
                            Icon(imageVector = Icons.Default.Shield, contentDescription = "Prevention", tint = MaterialTheme.colorScheme.secondary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = prev, fontSize = 14.sp)
                        }
                    }
                }
            }
        }

        item {
            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onFinish,
                modifier = Modifier.fillMaxWidth().height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(text = "Done / Return to Home")
            }
        }
    }
}
