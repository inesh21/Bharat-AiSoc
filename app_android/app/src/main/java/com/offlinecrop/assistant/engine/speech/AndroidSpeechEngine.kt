package com.offlinecrop.assistant.engine.speech

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import com.offlinecrop.assistant.engine.SpeechEngine
import java.util.Locale
import java.util.UUID

class AndroidSpeechEngine(context: Context) : SpeechEngine {
    private val main = Handler(Looper.getMainLooper())
    private var ready = false
    private var currentUtterance: String? = null
    private var onStatus: (Boolean, String?) -> Unit = { _, _ -> }
    private var tts: TextToSpeech? = null

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            main.post { ready = tts != null && status == TextToSpeech.SUCCESS }
        }
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String) = Unit
            override fun onDone(utteranceId: String) = complete(utteranceId, null)
            @Deprecated("Android invokes the error-code overload on supported platforms")
            override fun onError(utteranceId: String) = complete(utteranceId, "Playback failed.")
            override fun onError(utteranceId: String, errorCode: Int) =
                complete(utteranceId, "Playback failed.")
        })
    }

    private fun complete(id: String, error: String?) {
        main.post {
            if (currentUtterance == id) {
                currentUtterance = null
                onStatus(false, error)
            }
        }
    }

    fun observeStatus(listener: (Boolean, String?) -> Unit) {
        onStatus = listener
    }

    private fun offlineVoice(lang: String) = tts?.voices.orEmpty()
        .filter { it.locale.language == lang && !it.isNetworkConnectionRequired &&
            TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED !in it.features.orEmpty() }
        .maxByOrNull { it.quality }

    fun voiceAvailability(): Map<String, String?> =
        listOf("en", "hi", "te").associateWith { if (ready) offlineVoice(it)?.name else null }

    override fun speak(text: String, lang: String) {
        val engine = tts
        if (!ready || engine == null) {
            onStatus(false, "Text to speech is unavailable.")
            return
        }
        val voice = offlineVoice(lang)
        if (voice == null || engine.setVoice(voice) != TextToSpeech.SUCCESS) {
            val language = Locale.forLanguageTag(lang).getDisplayLanguage(Locale.ENGLISH)
            onStatus(false, "Install an offline $language voice in Android text-to-speech settings.")
            return
        }
        val id = UUID.randomUUID().toString()
        currentUtterance = id
        if (engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, id) == TextToSpeech.SUCCESS) {
            onStatus(true, null)
        } else {
            currentUtterance = null
            onStatus(false, "Playback failed.")
        }
    }

    override fun listen(lang: String): String = ""

    override fun stopSpeaking() {
        currentUtterance = null
        tts?.stop()
        onStatus(false, null)
    }

    override fun isSpeaking(): Boolean = currentUtterance != null

    fun shutdown() {
        stopSpeaking()
        tts?.shutdown()
        tts = null
        ready = false
    }
}
