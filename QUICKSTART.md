# Quick Start: Deploy to Device

This is the **fastest path** to get the app running on your Android device.

---

## Prerequisites Checklist

- ✅ Android device connected via USB (run `adb devices` to verify)
- ✅ USB debugging enabled on device
- ✅ At least 1 GB free storage on device
- ✅ Models already built: `models/vision_v1.pte` (13.1 MB) and `models/llama32_1b.pte` (821 MB)

---

## Option A: Deploy with Mocks (Fast - 5 minutes)

Use this to test the full UI flow without waiting for model transfer.

```bash
# 1. Build debug APK (uses mock engines)
cd app_android
./gradlew assembleDebug

# 2. Install
adb install app/build/outputs/apk/debug/app-debug.apk

# 3. Launch app
adb shell am start -n com.offlinecrop.assistant.debug/.MainActivity

# 4. Test
# - Select language
# - Simulate scan (choose "Early Blight" scenario)
# - View result and advisory
# - Test TTS (text-to-speech)
```

**What works:** All UI flows, mock predictions, clarifications, speech  
**What doesn't:** Real model inference

---

## Option B: Deploy with Real Models (Complete - 15-20 minutes)

### Step 1: Build Native Libraries

**Option 1 - Use LlamaDemo Reference (Recommended)**

```bash
# Copy JNI source from LlamaDemo
cp -r external/executorch-examples/llm/android/LlamaDemo/app/src/main/cpp/llama_jni.cpp \
      app_android/app/src/main/cpp/

# Update package name in llama_jni.cpp
# Find: com_example_executorchllamademo
# Replace: com_offlinecrop_assistant_engine_executorch

# Copy vision JNI template from PHASE5_INTEGRATION.md
# Create: app_android/app/src/main/cpp/vision_jni.cpp

# Add CMakeLists.txt (see PHASE5_INTEGRATION.md for template)
```

**Option 2 - Skip Native Build (Use Java Fallback)**

The engines will fall back to mocks if native libs aren't available. You can still test the UI flow.

### Step 2: Push Models to Device

**Windows:**
```batch
cd D:\bits\projects\AiSoc
app_android\push_models.bat
```

**Linux/Mac:**
```bash
cd /path/to/AiSoc
chmod +x app_android/push_models.sh
./app_android/push_models.sh
```

**Manual (if scripts fail):**
```bash
adb push models/vision_v1.pte /data/local/tmp/vision_v1.pte
adb push models/vision_v1.json /data/local/tmp/vision_v1.json
adb push models/llama32_1b.pte /data/local/tmp/llama32_1b.pte
adb push models_src/llama32_1b/tokenizer.model /data/local/tmp/tokenizer.model
```

This will take **5-10 minutes** (821 MB + 13 MB transfer).

### Step 3: Build Release APK

```bash
cd app_android

# Build release (uses real ExecuTorch engines)
./gradlew assembleRelease

# Install
adb install app/build/outputs/apk/release/app-release.apk
```

### Step 4: Test

```bash
# Enable airplane mode on device first!

# Launch app
adb shell am start -n com.offlinecrop.assistant/.MainActivity

# Watch logs
adb logcat | grep -E "ExecuTorch|MainActivity|CropAssistant"
```

**Test flow:**
1. Select language (English/Hindi/Telugu/Tamil/Kannada)
2. Take photo of a diseased leaf
3. View prediction (top-3 with confidence)
4. Read advisory (IPM steps, organic options, chemicals if needed)
5. Test TTS - listen to advice in local language
6. Test clarification (if ambiguous disease detected)

**Success criteria:**
- ✅ Vision inference completes (<1 sec)
- ✅ Advisory generation starts (TTFT <500ms)
- ✅ Tokens stream smoothly
- ✅ No crashes
- ✅ Works in airplane mode

---

## Troubleshooting

### "adb: device not found"
```bash
# Enable USB debugging on device:
# Settings → About phone → Tap "Build number" 7 times
# Settings → Developer options → USB debugging ON

# Reconnect USB cable
adb kill-server
adb start-server
adb devices
```

### "Model file not found"
```bash
# Verify files on device
adb shell ls -lh /data/local/tmp/*.pte

# If missing, re-run push script or manual push
```

### "UnsatisfiedLinkError: libexecutorch"
This means native JNI libraries weren't built. The app will fall back to mocks automatically.

To fix:
1. Follow PHASE5_INTEGRATION.md to build native libs
2. Or use debug build (mocks) for now

### App crashes on startup
```bash
# Check logcat for errors
adb logcat | grep -E "AndroidRuntime|FATAL"

# Common causes:
# - Missing assets (should be bundled in APK)
# - Out of memory (close other apps)
# - Corrupted model file (re-push)
```

### Inference is slow
```bash
# Check device specs
adb shell cat /proc/cpuinfo | grep -i "processor\|model"

# Expected performance on mid-range device:
# Vision: ~200-500ms per image
# Advisory TTFT: ~300-500ms
# Generation: ~10-20 tokens/sec
```

---

## Verification Checklist

### Milestone I2: Vision on Device
- [ ] Vision model loads without error
- [ ] Inference runs on real image
- [ ] Top-1 prediction matches test vector
- [ ] Severity estimation works
- [ ] Quality checks reject blurry/dark images

### Milestone I3: Advisory on Device  
- [ ] LLM model loads without error
- [ ] Advisory generates from vision result
- [ ] Tokens stream to UI
- [ ] Validator passes (no chemical hallucinations)
- [ ] Clarification loop works for ambiguous cases

### Milestone I4: End-to-End Offline
- [ ] Full scan works in airplane mode
- [ ] 20 diverse photos tested (healthy, diseased, pest, unknown)
- [ ] 0 crashes across all 20 scans
- [ ] All failure paths handled gracefully
- [ ] TTS works for all languages

---

## Next Steps After Deployment

1. **Record benchmarks** (use `benchmarks/benchmark_runner.py` as guide)
   - Vision latency per image
   - Advisory TTFT, tokens/sec
   - Peak RAM usage
   - Battery drain per scan

2. **Capture demo video** (2-3 minutes)
   - Show airplane mode indicator
   - Full scan flow: language → camera → result → advisory → TTS
   - Clarification question loop

3. **Run test vectors**
   - Vision: 50 images from `test_vectors/vision/parity_test_vectors.json`
   - Advisory: 30 prompts from `test_vectors/llm/parity.json`

4. **Update handoffs**
   - Record actual device metrics
   - Mark I2, I3, I4 as complete
   - Note any issues or limitations

---

## Need Help?

- **Integration guide:** `app_android/PHASE5_INTEGRATION.md`
- **Full status:** `PROJECT_STATUS.md`
- **Handoffs:** `docs/handoffs/track-{a,b,c}.md`
- **Contracts:** `docs/CONTRACTS.md`
- **Governance:** `AGENTS.md`

**Key insight:** The app is fully functional with mocks. Real model integration is the final 5% that requires JNI compilation and testing.
