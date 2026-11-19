# versions.md: Pinned versions

Everything here is pinned across all machines and the app. Change only through a decision record (`docs/decisions/`) and agreement of all three tracks.

| Item | Version / value | Notes |
|---|---|---|
| ExecuTorch | 1.4.0 (Maven Central / Release) | App runtime and all exported models must use this |
| PyTorch | 2.5.1 / 2.6.0 | Matches ExecuTorch 1.4.0 export requirement |
| Python | 3.11 / 3.12 | Recommended for ExecuTorch export wheel compatibility |
| Android Studio | Ladybug / Koala (2024.x) | Standard Android IDE |
| Android SDK / NDK | SDK 35 (Android 15), NDK 27.0.12077973 | Minimum SDK 26, Target SDK 35 |
| Target phone | Arm64 Android (e.g. 6GB-8GB RAM, Snapdragon/MediaTek) | Zero network requirement |
| Llama base model | Llama-3.2-1B-Instruct | Meta community license, quantized 8da4w |
| Vision backbone | MobileNetV3-Large (224x224 RGB) | ImageNet pretrained, quantized int8 |
| STT engine | Local Android SpeechRecognizer / Whisper tiny JNI | 100% offline |
| TTS engine | Android on-device TextToSpeech (Indic locales) | 100% offline |

## Working export commands (copy exactly what worked)

### Llama export
```bash
# ExecuTorch Llama export command (ExecuTorch 1.4.0)
python -m executorch.examples.models.llama.export_llama \
  --checkpoint models_src/llama32_1b/consolidated.00.pth \
  --params models_src/llama32_1b/params.json \
  --output_dir models/ \
  --quantization 8da4w \
  --max_seq_length 1024
```

### Vision export
```bash
# Vision MobileNetV3 export to ExecuTorch
python -m vision.export --model-weights models/vision_v1.pth --output models/vision_v1.pte
```

### Android build
```bash
cd app_android
./gradlew assembleDebug
```
