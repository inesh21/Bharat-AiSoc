#!/bin/bash
# Push models and test vectors to connected Android device
# Run from project root: ./app_android/push_models.sh

set -e

ADB="adb"
DEVICE_DIR="/data/local/tmp"

echo "=== Pushing models to Android device ==="
echo "Device: $($ADB devices | tail -n 2 | head -n 1)"

# Check device connection
if ! $ADB devices | grep -q "device$"; then
    echo "ERROR: No Android device connected"
    echo "Connect device and enable USB debugging"
    exit 1
fi

# Create device directory
echo "Creating device directory: $DEVICE_DIR"
$ADB shell mkdir -p $DEVICE_DIR 2>/dev/null || true

# Push vision model
echo ""
echo "Pushing vision_v1.pte (13.1 MB)..."
if [ -f "models/vision_v1.pte" ]; then
    $ADB push models/vision_v1.pte $DEVICE_DIR/vision_v1.pte
    echo "✓ Vision model pushed"
else
    echo "WARNING: models/vision_v1.pte not found"
fi

echo "Pushing vision_v1.json sidecar..."
if [ -f "models/vision_v1.json" ]; then
    $ADB push models/vision_v1.json $DEVICE_DIR/vision_v1.json
    echo "✓ Vision sidecar pushed"
else
    echo "WARNING: models/vision_v1.json not found"
fi

# Push LLM model
echo ""
echo "Pushing llama32_1b.pte (821 MB) - this will take ~2-3 minutes..."
if [ -f "models/llama32_1b.pte" ]; then
    $ADB push models/llama32_1b.pte $DEVICE_DIR/llama32_1b.pte
    echo "✓ LLM model pushed"
else
    echo "WARNING: models/llama32_1b.pte not found"
fi

echo "Pushing tokenizer.model..."
if [ -f "models_src/llama32_1b/tokenizer.model" ]; then
    $ADB push models_src/llama32_1b/tokenizer.model $DEVICE_DIR/tokenizer.model
    echo "✓ Tokenizer pushed"
else
    echo "WARNING: models_src/llama32_1b/tokenizer.model not found"
fi

# Push test vectors (optional)
echo ""
echo "Pushing test vectors..."
if [ -f "test_vectors/vision/parity_test_vectors.json" ]; then
    $ADB push test_vectors/vision/parity_test_vectors.json $DEVICE_DIR/
    echo "✓ Vision test vectors pushed"
fi

if [ -f "test_vectors/llm/parity.json" ]; then
    $ADB push test_vectors/llm/parity.json $DEVICE_DIR/
    echo "✓ LLM test vectors pushed"
fi

# Verify files on device
echo ""
echo "=== Files on device ==="
$ADB shell ls -lh $DEVICE_DIR/*.pte $DEVICE_DIR/*.json $DEVICE_DIR/*.model 2>/dev/null || true

echo ""
echo "=== Model push complete ==="
echo "Next steps:"
echo "1. Build APK: cd app_android && ./gradlew assembleRelease"
echo "2. Install: adb install app/build/outputs/apk/release/app-release.apk"
echo "3. Test in airplane mode with 20 real photos (Milestone I4)"
