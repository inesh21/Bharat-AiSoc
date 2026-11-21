# Android device self-test

Use the release APK on an Arm64 phone. The app expects the vision sidecar,
vision model, Llama model and tokenizer in the app's external files
models directory. See app_android/PUSH_MODELS.md.

Generate the bundle using Track A's vision/make_device_vectors.py. From
the project root, copy it to the phone:

    adb push test_vectors/vision/device_vectors.zip /sdcard/Android/data/com.offlinecrop.assistant/files/device_vectors.zip

Turn airplane mode on and Wi-Fi off. Open **Device self-test** from the
language screen and tap **Run checks**. The app compares model logits and
top predictions on all 50 raw tensors and their matching PNGs. The advisory
suite runs 30 synthetic inputs over English, Hindi and Telugu. A valid
fallback keeps the advisory usable and is counted separately from an
accepted generation. The runner also checks poor-quality and unknown
inputs and rejects invalid or additional fields in generated selections.

Pull the result after the summary appears:

    adb pull /sdcard/Android/data/com.offlinecrop.assistant/files/self-test.csv benchmarks/results.csv

The CSV includes ten image-to-advisory runs when at least one image passes
quality and confidence checks. Inputs cycle if fewer than ten qualify.
Pipeline wall time
starts at PNG decode and includes loading both models on demand. Vision
parity timings cover the raw tensor forward pass. First-token wall time
includes lazy Llama loading when required. Decode throughput is from
ExecuTorch. Peak RSS is the process high-water mark, so it can include
work from earlier rows. Temperature is the reported battery temperature.
The initial voice check reports installed offline voice candidates.

Exercise the live camera and local photo picker separately. The reference
PNGs match the model input dimensions. They measure inference parity and
cannot establish field accuracy or end-to-end camera coverage. The target
hardware, field photos, offline playback, and ambiguous-photo checks
belong in the corresponding milestone evidence.

## Demo smoke test

Keep airplane mode on and Wi-Fi off. Choose English or Hindi and open
the camera. Confirm the preview and shutter work. A dark or blurred
frame should offer a retake without starting Llama.

For a repeatable positive case, extract device/img_010.png from the
generated bundle and place it in the phone's Downloads folder. Choose
that local photo in the app and open the treatment advisory. The A142
showed cotton bacterial blight and played the sourced advisory offline
in English and Hindi. Telugu text worked and the phone prompted for an
offline Telugu voice.

This check covers a known reference photo and a camera rejection path.
The 20-photo field exit check, capture-to-advisory latency and the five
ambiguous-photo checks still require separate device evidence.
