# Phase 5: ExecuTorch Integration Guide

This document describes how to complete the ExecuTorch integration for the Android app.

## Status

✅ **Completed:**
- Phase 4.1: Android assets exported (5 JSON files in `app/src/main/assets/`)
- Phase 4.2: Kotlin logic ported (6 classes in `com.offlinecrop.assistant.logic`)
- Phase 5.3: `ExecuTorchVisionEngine.kt` implemented
- Phase 5.4: `ExecuTorchAdvisoryEngine.kt` implemented
- Phase 5.5: `MainActivity.kt` updated to use real engines with USE_MOCKS flag

🔧 **Remaining:**
- Phase 5.1: Build and integrate ExecuTorch AAR
- Phase 5.2: Build native JNI libraries for vision and LLM inference

---

## Phase 5.1: ExecuTorch AAR Integration

### Option A: Use Pre-built AAR from ExecuTorch Release

1. Download ExecuTorch 1.6.0 AAR from releases or build locally
2. Place in `app_android/app/libs/executorch-android-1.6.0.aar`
3. Uncomment line 120 in `app/build.gradle.kts`:
   ```kotlin
   implementation(fileTree(mapOf("dir" to "libs", "include" to listOf("*.aar"))))
   ```

### Option B: Reference from LlamaDemo Example

The `external/executorch-examples/llm/android/LlamaDemo` was successfully built and tested.
You can reference its native libraries directly:

```bash
cd external/executorch-examples/llm/android/LlamaDemo
./gradlew assembleDebug
```

Then copy the built native libraries from:
- `LlamaDemo/app/build/intermediates/stripped_native_libs/debug/out/lib/`

---

## Phase 5.2: Native JNI Libraries

### Required JNI Wrappers

Two new native library modules are needed:

#### 1. **libvision_jni.so** - Vision inference wrapper

Create `app_android/app/src/main/cpp/vision_jni.cpp`:

```cpp
#include <jni.h>
#include <android/log.h>
#include <executorch/extension/module/module.h>

using namespace torch::executor;

extern "C" {

JNIEXPORT jlong JNICALL
Java_com_offlinecrop_assistant_engine_executorch_ExecuTorchVisionEngine_nativeLoadModule(
    JNIEnv* env, jobject, jstring modelPath) {
    
    const char* path = env->GetStringUTFChars(modelPath, nullptr);
    
    auto module = std::make_unique<Module>(path, Module::MlockConfig::UseMlock);
    
    env->ReleaseStringUTFChars(modelPath, path);
    
    return reinterpret_cast<jlong>(module.release());
}

JNIEXPORT jfloatArray JNICALL
Java_com_offlinecrop_assistant_engine_executorch_ExecuTorchVisionEngine_nativeForward(
    JNIEnv* env, jobject, jlong handle, jfloatArray input) {
    
    Module* module = reinterpret_cast<Module*>(handle);
    
    // Get input array
    jfloat* inputData = env->GetFloatArrayElements(input, nullptr);
    jsize inputSize = env->GetArrayLength(input);
    
    // Create input tensor (1, 3, 224, 224)
    std::vector<int32_t> sizes = {1, 3, 224, 224};
    auto inputTensor = torch::executor::from_blob(
        inputData, sizes, torch::executor::ScalarType::Float);
    
    // Run inference
    auto result = module->forward({inputTensor});
    
    // Extract output logits (18 classes)
    auto outputTensor = result[0].toTensor();
    float* outputData = outputTensor.data_ptr<float>();
    int numClasses = outputTensor.size(1);
    
    // Copy to Java array
    jfloatArray output = env->NewFloatArray(numClasses);
    env->SetFloatArrayRegion(output, 0, numClasses, outputData);
    
    env->ReleaseFloatArrayElements(input, inputData, JNI_ABORT);
    
    return output;
}

JNIEXPORT void JNICALL
Java_com_offlinecrop_assistant_engine_executorch_ExecuTorchVisionEngine_nativeUnloadModule(
    JNIEnv*, jobject, jlong handle) {
    
    Module* module = reinterpret_cast<Module*>(handle);
    delete module;
}

} // extern "C"
```

#### 2. **libllama_jni.so** - LLM inference wrapper

You can reference the existing implementation from `external/executorch-examples/llm/android/LlamaDemo/app/src/main/cpp/`.

The LlamaDemo already provides:
- `llama_jni.cpp` - JNI bindings for Llama inference
- `LlmModule` integration
- Token streaming callbacks

**To integrate:**

1. Copy JNI source from LlamaDemo:
   ```bash
   cp -r external/executorch-examples/llm/android/LlamaDemo/app/src/main/cpp/* \
         app_android/app/src/main/cpp/llm/
   ```

2. Update package name in JNI methods from:
   - `com_example_executorchllamademo` → `com_offlinecrop_assistant_engine_executorch`

3. Add `CMakeLists.txt` to `app_android/app/`:
   ```cmake
   cmake_minimum_required(VERSION 3.22.1)
   project(crop_assistant_native)
   
   # ExecuTorch
   find_library(EXECUTORCH_LIB executorch REQUIRED)
   find_library(EXTENSION_MODULE_LIB extension_module REQUIRED)
   
   # Vision JNI
   add_library(vision_jni SHARED src/main/cpp/vision_jni.cpp)
   target_link_libraries(vision_jni ${EXECUTORCH_LIB} ${EXTENSION_MODULE_LIB} log)
   
   # LLM JNI (use LlamaDemo implementation)
   add_library(llama_jni SHARED src/main/cpp/llm/llama_jni.cpp)
   target_link_libraries(llama_jni ${EXECUTORCH_LIB} log)
   ```

4. Update `app/build.gradle.kts` to enable CMake:
   ```kotlin
   android {
       externalNativeBuild {
           cmake {
               path = file("CMakeLists.txt")
               version = "3.22.1"
           }
       }
   }
   ```

---

## Phase 5.6: Push Models to Device

```bash
# Vision model
adb push models/vision_v1.pte /data/local/tmp/vision_v1.pte
adb push models/vision_v1.json /data/local/tmp/vision_v1.json

# LLM model
adb push models/llama32_1b.pte /data/local/tmp/llama32_1b.pte
adb push models_src/llama32_1b/tokenizer.model /data/local/tmp/tokenizer.model

# Test vectors (optional, for on-device validation)
adb push test_vectors/vision/parity_test_vectors.json /data/local/tmp/
adb push test_vectors/llm/parity.json /data/local/tmp/
```

---

## Phase 5.7: Build and Test

### Build APK

```bash
cd app_android

# Debug build (uses mocks)
./gradlew assembleDebug

# Release build (uses real ExecuTorch engines)
./gradlew assembleRelease
```

### Install and Test

```bash
# Install
adb install app/build/outputs/apk/debug/app-debug.apk

# Or for release
adb install app/build/outputs/apk/release/app-release.apk

# Check logs
adb logcat | grep -E "ExecuTorch|MainActivity|CropAssistant"
```

### Verify Milestones

**I2: Vision on device**
- Run 50 test vectors from `test_vectors/vision/parity_test_vectors.json`
- Verify predictions match within tolerance

**I3: Advisory on device**
- Run 30 test prompts from `test_vectors/llm/parity.json`
- Verify advisory validation passes

**I4: End-to-end offline**
- Enable airplane mode
- Take 20 real photos
- Verify zero crashes, complete flow works

---

## Troubleshooting

### ExecuTorch library not found
- Verify AAR is in `app/libs/` and build.gradle.kts line is uncommented
- Check `System.loadLibrary()` calls in engine constructors

### UnsatisfiedLinkError
- Verify native libraries are built and included in APK
- Check ABI filters in build.gradle.kts: `abiFilters.addAll(listOf("arm64-v8a"))`

### Model file not found
- Verify files were pushed to `/data/local/tmp/`
- Check permissions: `adb shell ls -la /data/local/tmp/*.pte`

### Inference crashes
- Check logcat for segfaults or memory errors
- Verify model format matches ExecuTorch 1.6.0
- Test with smaller input first

---

## Alternative: Use Mock Engines for Testing

If ExecuTorch integration is blocked, the app can run with mocks:

1. Keep `BuildConfig.USE_MOCKS = true` in debug builds
2. All UI flows work with synthetic data
3. Test vector validation can run on laptop Python

The mock engines are production-quality implementations of the contracts.
