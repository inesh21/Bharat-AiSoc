# versions.md: Pinned versions

Everything here is pinned across all machines and the app. Change only through a decision record (`docs/decisions/`) and agreement of all three tracks.

| Item | Version / value | Notes |
|---|---|---|
| ExecuTorch | 1.6.0 (Python wheel, source tree in executorch/) | App runtime and all exported models must use this |
| PyTorch (export env) | 2.15.0.dev20261005+cpu (nightly) | Required for executorch==1.6.0; install with `--index-url https://download.pytorch.org/whl/nightly/cpu` |
| PyTorch (train env) | 2.6.0+cu124 (or 2.5.x+cpu) | CUDA not needed for export; use a separate env or reinstall for export |
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
# ExecuTorch Llama export command (ExecuTorch 1.6.0 on Python 3.12)
# Config: llm/export/llama32_1b_xnnpack.yaml
.\.venv-et\Scripts\python.exe llm/export/run_export.py --config llm/export/llama32_1b_xnnpack.yaml
# Output: models/llama32_1b.pte (821 MB, 8da4w_xnnpack, context length: 1024)
# SHA-256: 2b25c581c9894bfed83a2f23385be33e977850c186caf276f2bdc53a43d06f6f
```

### Vision export
```powershell
# Vision MobileNetV3-Large export to ExecuTorch .pte (run from project root)
# Requires: torch==2.15.0.dev20261005+cpu + torchvision==0.30.0.dev20261005+cpu + executorch==1.6.0
# Install torch nightly first:
#   .\.venv-et\Scripts\python.exe -m pip install "torch==2.15.0.dev20261005+cpu" "torchvision==0.30.0.dev20261005+cpu" --index-url https://download.pytorch.org/whl/nightly/cpu
.\.venv-et\Scripts\python.exe vision\export_pte.py
# Output: models/vision_v1.pte (13.1 MB, executorch-xnnpack, 18 classes, 224x224 RGB)
# SHA-256: a288ac81cf683a5a6124fbb6e8cf5759f0c18fdb4f24b9e03505bc8be3cd5649
# Parity test:
.\.venv-et\Scripts\python.exe vision\parity_test.py
# → max_abs_diff=5.96e-06, all 50 top-1 predictions match between PT and ET
```

### Android build
```bash
cd app_android
./gradlew assembleDebug
```
