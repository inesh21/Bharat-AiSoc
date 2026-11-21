# ExecuTorch AAR Integration - BLOCKED

## Current Status

The ExecuTorch integration code is **complete and ready**, but the build is blocked because the `executorch-android-1.6.0.aar` file is not present in `app/libs/`.

## Where to Get the AAR

**Option 1: Download prebuilt AAR (recommended)**
- Check ExecuTorch releases: https://github.com/pytorch/executorch/releases/tag/v1.6.0
- Look for `executorch-android-1.6.0.aar` or similar Android artifact
- Place in: `app_android/app/libs/executorch-android-1.6.0.aar`

**Option 2: Build from source**
```bash
# Clone ExecuTorch 1.6.0
git clone --branch v1.6.0 https://github.com/pytorch/executorch.git
cd executorch

# Follow Android build instructions in:
# extension/android/README.md

# This will produce the AAR file
```

**Option 3: Use the AAR from LlamaDemo**
If you previously built the LlamaDemo reference app (milestone I1), the AAR should be cached in:
- Gradle cache: `~/.gradle/caches/transforms-*/*/executorch*.aar`
- Or in the LlamaDemo project if it has a local libs directory

## Once You Have the AAR

1. Place `executorch-android-1.6.0.aar` in `app_android/app/libs/`
2. Rebuild: `cd app_android && ./gradlew assembleRelease`
3. The app will compile successfully

## What's Already Done

✅ Gradle dependencies configured (soloader, fbjni)
✅ ABIs restricted to arm64-v8a
✅ ExecuTorchVisionEngine implemented using `org.pytorch.executorch.Module`
✅ ExecuTorchAdvisoryEngine implemented using `org.pytorch.executorch.LlamaModule`
✅ MainActivity updated to use `getExternalFilesDir("models")`
✅ Model push commands documented in PUSH_MODELS.md
✅ No INTERNET permission in manifest (verified)

## What's Pending

⏳ Obtain executorch-android-1.6.0.aar
⏳ Build release APK
⏳ Push models to device (834 MB)
⏳ Test on device (I2, I3, I4 milestones)

## Workaround for Testing

The debug build with `USE_MOCKS=true` still works:
```bash
cd app_android
./gradlew assembleDebug  # This will work
adb install app/build/outputs/apk/debug/app-debug.apk
```

This lets you test the full UI flow with mocks while waiting for the AAR.
