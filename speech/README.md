# Speech & Audio Subsystem (Track C - Task C9)

This module handles offline voice interactions (TTS and STT) for the Offline Crop Disease Assistant.

## Key Design Principles
1. **Zero Internet:** All speech synthesis and recognition occur locally on the Android device.
2. **Offline TTS (`AndroidSpeechEngine`):**
   - Direct JNI/platform integration with Android's on-device `TextToSpeech` service.
   - Fallback and routing across Indic locales (`hi-IN`, `te-IN`, `ta-IN`, `kn-IN`, `mr-IN`) and English (`en-IN` / `en-US`).
3. **Offline STT (`SpeechEngine.listen`):**
   - Designed to interface with local Whisper tiny/base via whisper.cpp JNI or Vosk offline recognizer.
