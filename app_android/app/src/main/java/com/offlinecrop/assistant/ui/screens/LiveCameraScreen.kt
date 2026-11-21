package com.offlinecrop.assistant.ui.screens

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import java.io.File

@Composable
internal fun LiveCameraScreen(
    busy: Boolean,
    onImage: (Uri, File?) -> Unit,
) {
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current
    val executor = remember(context) { ContextCompat.getMainExecutor(context) }
    val view = remember(context) { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FIT_CENTER } }
    var permission by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED)
    }
    var capture by remember { mutableStateOf<ImageCapture?>(null) }
    var capturing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val requestCamera = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        permission = granted
        error = if (granted) null else "Camera access was denied. You can select a local photo."
    }
    val gallery = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {
        if (it != null) onImage(it, null)
    }

    if (permission) {
        DisposableEffect(lifecycle, view) {
            var disposed = false
            var provider: ProcessCameraProvider? = null
            val preview = Preview.Builder().build()
            val imageCapture = ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY).build()
            val pendingProvider = ProcessCameraProvider.getInstance(context)
            pendingProvider.addListener({
                if (!disposed) {
                    try {
                        provider = pendingProvider.get()
                        preview.setSurfaceProvider(view.surfaceProvider)
                        provider!!.bindToLifecycle(lifecycle, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageCapture)
                        capture = imageCapture
                    } catch (e: Exception) {
                        error = "Camera is unavailable. Select a local photo."
                    }
                }
            }, executor)
            onDispose {
                disposed = true
                provider?.unbind(preview, imageCapture)
                capture = null
            }
        }
    }

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Photograph a leaf", style = MaterialTheme.typography.headlineSmall)
        Text("Use natural light and fill the frame with one leaf.")
        if (permission) {
            AndroidView(factory = { view }, modifier = Modifier.fillMaxWidth().weight(1f))
        } else {
            Button(onClick = { requestCamera.launch(Manifest.permission.CAMERA) }, enabled = !busy) {
                Text("Enable camera")
            }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val currentCapture = capture
            Button(
                enabled = currentCapture != null && !busy && !capturing,
                onClick = {
                    if (currentCapture != null) {
                        capturing = true
                        error = null
                        try {
                            capturePhoto(context, view, currentCapture, onImage) { message ->
                                capturing = false
                                error = message
                            }
                        } catch (e: Exception) {
                            capturing = false
                            error = "Could not save the photo. Try again."
                        }
                    }
                },
            ) {
                Text("Take photo")
            }
            OutlinedButton(
                onClick = { gallery.launch("image/*") },
                enabled = !busy && !capturing,
            ) {
                Text("Choose photo")
            }
        }
    }
}

private fun capturePhoto(
    context: Context,
    view: PreviewView,
    capture: ImageCapture,
    onImage: (Uri, File?) -> Unit,
    onComplete: (String?) -> Unit,
) {
    val file = File.createTempFile("leaf-", ".jpg", context.cacheDir)
    view.display?.let { capture.targetRotation = it.rotation }
    try {
        capture.takePicture(
            ImageCapture.OutputFileOptions.Builder(file).build(),
            ContextCompat.getMainExecutor(context),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(result: ImageCapture.OutputFileResults) {
                    onComplete(null)
                    onImage(Uri.fromFile(file), file)
                }

                override fun onError(exception: ImageCaptureException) {
                    file.delete()
                    onComplete("Could not capture the photo. Try again.")
                }
            },
        )
    } catch (e: Exception) {
        file.delete()
        throw e
    }
}
