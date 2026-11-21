package com.offlinecrop.assistant.logic

import org.json.JSONObject

/**
 * LanguageLayer – Kotlin port of llm/language_layer.py (Phase 4.2).
 *
 * Localises an advisory response for regional languages using slot-based
 * templates grounded in verified agrarian terminology.  English passes
 * through unmodified.
 *
 * Pure Kotlin – no Android imports.
 */
class LanguageLayer(phrasesJson: String) {

    // Map lang -> phrase key -> phrase text
    private val phrases: Map<String, Map<String, String>>

    init {
        val root = JSONObject(phrasesJson)
        val mutable = mutableMapOf<String, Map<String, String>>()
        val langs = root.keys()
        while (langs.hasNext()) {
            val lang = langs.next()
            val phraseObj = root.getJSONObject(lang)
            val inner = mutableMapOf<String, String>()
            val pKeys = phraseObj.keys()
            while (pKeys.hasNext()) {
                val k = pKeys.next()
                inner[k] = phraseObj.getString(k)
            }
            mutable[lang] = inner
        }
        phrases = mutable
    }

    /**
     * Localises [advisory] for [lang].
     * Mirrors llm/language_layer.py::localize_advisory().
     */
    fun localise(advisory: AdvisoryResponseData, lang: String): AdvisoryResponseData {
        if (lang == "en" || !phrases.containsKey(lang)) return advisory

        val p = phrases[lang] ?: return advisory
        val diag = advisory.diagnosis
        val actions = advisory.actionsNow

        val locText = buildString {
            append("${p["diagnosis_prefix"]} $diag. ")
            if (actions.isNotEmpty()) append("${p["actions_prefix"]} ${actions[0]} ")
        }

        return advisory.copy(language = lang, text = locText)
    }

    /**
     * Returns the localised phrase for [key] in [lang], falling back to English.
     */
    fun phrase(lang: String, key: String): String {
        return phrases[lang]?.get(key)
            ?: phrases["en"]?.get(key)
            ?: ""
    }
}
