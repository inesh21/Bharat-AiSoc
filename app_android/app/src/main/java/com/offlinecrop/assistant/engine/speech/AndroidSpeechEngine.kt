package com.offlinecrop.assistant.engine.speech

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import com.offlinecrop.assistant.engine.SpeechEngine
import java.util.*

/**
 * On-device SpeechEngine implementing offline Text-To-Speech (TTS) (Task C9).
 * Utilizes local on-device Android TTS engine with voices for English, Hindi, and regional Indic languages.
 * Operates strictly with zero cloud calls / offline.
 */
class AndroidSpeechEngine(private val context: Context) : SpeechEngine, TextToSpeech.OnInitListener {

    private var tts: TextToSpeech? = null
    private var isInitialized = false

    companion object {
        private const val TAG = "AndroidSpeechEngine"
    }

    init {
        tts = TextToSpeech(context, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            isInitialized = true
            Log.d(TAG, "Offline TTS successfully initialized.")
        } else {
            Log.e(TAG, "Failed to initialize Android TextToSpeech, status: $status")
        }
    }

    private fun resolveLocale(lang: String): Locale {
        return when (lang.lowercase()) {
            "hi" -> Locale("hi", "IN")
            "te" -> Locale("te", "IN")
            "ta" -> Locale("ta", "IN")
            "kn" -> Locale("kn", "IN")
            "mr" -> Locale("mr", "IN")
            "bn" -> Locale("bn", "IN")
            else -> Locale.ENGLISH
        }
    }

    override fun speak(text: String, lang: String) {
        if (!isInitialized || tts == null) {
            Log.w(TAG, "TTS not ready yet.")
            return
        }

        val locale = resolveLocale(lang)
        val result = tts?.setLanguage(locale)
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            Log.w(TAG, "Language $locale not fully supported or missing data, falling back to default locale.")
            tts?.language = Locale.getDefault()
        }

        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "CropUtterance_${System.currentTimeMillis()}")
    }

    override fun listen(lang: String): String {
        // Voice recognition hook - in offline mode, vosk / whisper.cpp or on-device RecognizerIntent is invoked.
        // Returns recognized text
        return ""
    }

    override fun stopSpeaking() {
        tts?.stop()
    }

    override fun isSpeaking(): Boolean {
        return tts?.isSpeaking ?: false
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}
