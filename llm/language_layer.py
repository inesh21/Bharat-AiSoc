"""Multilingual localization and translation layer (Task B9).

Llama generates directly for supported languages (e.g. English, Hindi).
For regional languages (Telugu, Tamil, Kannada, Marathi), this module provides:
1. Slot-based templating grounded in verified agrarian terminology
2. Clean key translations for UI & TTS readouts
"""

from typing import Dict, Any, List

# Core diagnostic phrase mappings across regional languages
LOCALIZED_PHRASES: Dict[str, Dict[str, str]] = {
    "hi": {
        "diagnosis_prefix": "निदान (रोग पहचान):",
        "actions_prefix": "तुरंत किए जाने वाले उपाय:",
        "prevention_prefix": "दीर्घकालिक रोकथाम:",
        "unknown_warning": "यह लक्षण स्पष्ट नहीं है। कृपया नजदीकी कृषि विज्ञान केंद्र (KVK) के अधिकारी से संपर्क करें।",
        "healthy_msg": "आपकी फसल स्वस्थ दिखाई दे रही है। नियमित देखभाल जारी रखें।"
    },
    "te": {
        "diagnosis_prefix": "వ్యాధి నిర్ధారణ:",
        "actions_prefix": "తక్షణ నివారణ చర్యలు:",
        "prevention_prefix": "దీర్ఘకాలిక జాగ్రత్తలు:",
        "unknown_warning": "లక్షణాలు ఖచ్చితంగా గుర్తించబడలేదు. దయచేసి స్థానిక వ్యవసాయ అధికారి లేదా కేవీకేను సంప్రదించండి.",
        "healthy_msg": "మీ పంట ఆరోగ్యంగా ఉంది. సాధారణ యాజమాన్య పద్ధతులను కొనసాగించండి."
    },
    "ta": {
        "diagnosis_prefix": "நோய் கண்டறிதல்:",
        "actions_prefix": "உடனடி மேலாண்மை முறைகள்:",
        "prevention_prefix": "நீண்ட கால தடுப்பு நடவடிக்கைகள்:",
        "unknown_warning": "அறிகுறிகள் தெளிவாக கண்டறியப்படவில்லை. அருகில் உள்ள வேளாண்மை அறிவியல் மையத்தை அணுகவும்.",
        "healthy_msg": "பயிர் ஆரோக்கியமாக உள்ளது. வழக்கமான பராமரிப்பை தொடரவும்."
    },
    "kn": {
        "diagnosis_prefix": "ರೋಗ ಪತ್ತೆ:",
        "actions_prefix": "ತಕ್ಷಣದ ಕ್ರಮಗಳು:",
        "prevention_prefix": "ದೀರ್ಘಕಾಲೀನ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು:",
        "unknown_warning": "ರೋಗಲಕ್ಷಣಗಳು ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರದ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "healthy_msg": "ಬೆಳೆ ಆರೋಗ್ಯಕರವಾಗಿದೆ. ಸಾಮಾನ್ಯ ಪೋಷಣೆಯನ್ನು ಮುಂದುವರಿಸಿ."
    }
}


def localize_advisory(advisory_data: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Translates advisory structure to regional language using verified slots if lang != 'en'."""
    if lang == "en" or lang not in LOCALIZED_PHRASES:
        return advisory_data

    phrases = LOCALIZED_PHRASES[lang]
    diag = advisory_data.get("diagnosis", "")
    actions = advisory_data.get("actions_now", [])
    prev = advisory_data.get("prevention", [])

    localized_text = f"{phrases['diagnosis_prefix']} {diag}. "
    if actions:
        localized_text += f"{phrases['actions_prefix']} {actions[0]} "

    result = dict(advisory_data)
    result["language"] = lang
    result["text"] = localized_text
    return result
