# Model Push Commands

These commands push the 4 model files from your PC to the Android device's external files directory for the app.

## Prerequisites

1. Device connected via USB with debugging enabled
2. Run `adb devices` to verify connection
3. Models exist in `D:\bits\projects\AiSoc\models\` and `models_src\`

## Get the app's external files directory path

First, find the exact path (it varies by device):

```bash
adb shell run-as com.offlinecrop.assistant ls /data/data/com.offlinecrop.assistant/files
```

Or for release APK without debuggable flag, use:

```bash
adb shell "ls /sdcard/Android/data/com.offlinecrop.assistant/files/"
```

## Push commands (834 MB total)

**For app with debug flag (development):**

```bash
# Create models directory
adb shell "run-as com.offlinecrop.assistant mkdir -p /data/data/com.offlinecrop.assistant/files/models"

# Push vision model (13.1 MB)
adb push models/vision_v1.pte /data/local/tmp/vision_v1.pte
adb shell "run-as com.offlinecrop.assistant cp /data/local/tmp/vision_v1.pte /data/data/com.offlinecrop.assistant/files/models/vision_v1.pte"

# Push vision sidecar (2 KB)
adb push models/vision_v1.json /data/local/tmp/vision_v1.json
adb shell "run-as com.offlinecrop.assistant cp /data/local/tmp/vision_v1.json /data/data/com.offlinecrop.assistant/files/models/vision_v1.json"

# Push Llama model (821 MB - takes 5-10 minutes)
adb push models/llama32_1b.pte /data/local/tmp/llama32_1b.pte
adb shell "run-as com.offlinecrop.assistant cp /data/local/tmp/llama32_1b.pte /data/data/com.offlinecrop.assistant/files/models/llama32_1b.pte"

# Push tokenizer (2 MB)
adb push models_src/llama32_1b/tokenizer.model /data/local/tmp/tokenizer.model
adb shell "run-as com.offlinecrop.assistant cp /data/local/tmp/tokenizer.model /data/data/com.offlinecrop.assistant/files/models/tokenizer.model"

# Verify
adb shell "run-as com.offlinecrop.assistant ls -lh /data/data/com.offlinecrop.assistant/files/models/"
```

**For release APK (use external storage):**

```bash
# Get package-specific external directory
EXTERNAL_DIR="/sdcard/Android/data/com.offlinecrop.assistant/files/models"

adb shell "mkdir -p $EXTERNAL_DIR"

# Push all 4 files directly
adb push models/vision_v1.pte $EXTERNAL_DIR/vision_v1.pte
adb push models/vision_v1.json $EXTERNAL_DIR/vision_v1.json
adb push models/llama32_1b.pte $EXTERNAL_DIR/llama32_1b.pte
adb push models_src/llama32_1b/tokenizer.model $EXTERNAL_DIR/tokenizer.model

# Verify
adb shell "ls -lh $EXTERNAL_DIR"
```

## Expected output after push

```
-rw-rw-rw- 1 u0_a123 u0_a123  13M 2026-11-21 vision_v1.pte
-rw-rw-rw- 1 u0_a123 u0_a123 2.0K 2026-11-21 vision_v1.json
-rw-rw-rw- 1 u0_a123 u0_a123 821M 2026-11-21 llama32_1b.pte
-rw-rw-rw- 1 u0_a123 u0_a123 2.0M 2026-11-21 tokenizer.model
```

## Notes

- External files directory (`getExternalFilesDir("models")`) requires no special permissions
- This directory is automatically created when the app first runs
- Files are removed when the app is uninstalled
- The large Llama model transfer will take 5-10 minutes over USB
