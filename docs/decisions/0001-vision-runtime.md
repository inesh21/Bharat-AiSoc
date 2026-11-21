# 0001: Vision runtime
Date: 2026-11-19
Status: accepted
Deciders: Track A, Track C humans (Track B informed)

## Context
Llama must run on ExecuTorch. The vision model could use the same runtime or another. One runtime is simpler to build, document and explain. Decision needed by Day 3 so Track A can plan the export and Track C can plan the app.

## Options considered
1. ExecuTorch (XNNPACK) for vision as well (one runtime story, one set of native libraries in the app).
2. ONNX Runtime or TFLite for vision only (possibly easier model conversion for some architectures).

## Decision
Option 1: ExecuTorch (XNNPACK) is selected as the unified runtime for both Vision (MobileNetV3) and Advisory (Llama 3.2 1B). This allows a single C++/JNI native library footprint in the Android app.

## Consequences
- Track A exports according to ExecuTorch EXIR / XNNPACK flow (`models/vision_v1.pte`).
- Track C includes `org.pytorch:executorch-android:1.4.0` in the app and keeps `VisionEngine` behind the clean interface in `Contracts.kt`.
