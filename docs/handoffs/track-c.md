# Handoff: Track C: App, Voice and Integration

**Active agent:** none
**Owner (human):** ________
**Branch / worktree:** track-c/main  ->  ../crop-wt/track-c
**Task IDs:** C1 to C13 (see `docs/tracks/TRACK_C_APP.md`)
**Last updated:** 2026-11-20

## Milestone status

| Milestone | Status | Evidence |
|---|---|---|
| I0 Contracts frozen | done | Contracts implemented in Kotlin and validated against mocks |
| I1 Runtime proven | done | Reference ExecuTorch LlamaDemo deployed on device; on-device TTFT 367ms, 15.27 t/s benchmarked |
| I2 Vision on device | in progress | UI ready; `ExecuTorchVisionEngine` stub needed (Phase 5.3) |
| I3 Advisory on device | in progress | Kotlin advisory logic ported; `ExecuTorchAdvisoryEngine` stub needed (Phase 5.4) |
| I4 End to end offline | in progress | Manifest audited: zero INTERNET permission, 100% offline |
| I5 Voice and clarifications | in progress | Clarification UI loop and Android SpeechEngine implemented |
| I6 Freeze and polish | not started | |

## Requests to other tracks (open)

- To Track A: Need `models/vision_v1.pte` and `test_vectors/vision/` to verify on-device ExecuTorch vision inference. | CONTRACTS.md Section 7 | needed for I2 | status: open
- To Track B: Need `models/llama_v1.pte` and tokenizer files for background generation streaming. | CONTRACTS.md Section 7 | needed for I3 | status: open

## Requests from other tracks (handled)

- Handled request from Track A: Received `labels.json` and standard normalization spec (mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225]). Configured in app preprocessing.

## Session log (newest first)

### Session 2026-11-20 00:00 | agent: antigravity | branch: integration
Task IDs: C8 (Kotlin logic port), Phase 4.1–4.4

**Summary**
Phase 4.1 and 4.2 completed. Android assets exported, Kotlin logic package fully ported from Python,
parity test suite passes. Build infrastructure fixed (gradle.properties, missing icons, ExecuTorch AAR stub).

**Done** (with evidence)
- `app_android/app/src/main/assets/` – 5 JSON assets exported (`kb.json`, `rules.json`, `clarifications.json`, `phrases.json`, `labels.json`) via `tools/export_for_android.py`.
- `app_android/app/src/main/java/com/offlinecrop/assistant/logic/` – 6 Kotlin classes ported (no Android dependencies, JVM-testable):
  - `KnowledgeRepository` (port of `knowledge/retrieval.py`)
  - `ClarificationEngine` (port of `knowledge/clarifications.py`)
  - `PromptBuilder` (port of `llm/prompts.py`)
  - `AdvisoryValidator` (port of `llm/validator.py`)
  - `LanguageLayer` (port of `llm/language_layer.py`)
  - `AdvisoryPipeline` (port of `llm/pipeline.py`)
- `app_android/app/src/test/java/com/offlinecrop/assistant/logic/ParityTest.kt` – 3 test methods, 33 total assertions; `BUILD SUCCESSFUL` confirmed.
- `app_android/gradle.properties` – created (was missing); `android.useAndroidX=true` fixes AndroidX detection.
- `app_android/app/build.gradle.kts` – removed `org.pytorch:executorch-android:0.4.0` placeholder (artifact doesn't exist); documented Phase 5 AAR path.
- `app_android/app/libs/.gitkeep` – stub directory for ExecuTorch 1.6.0 AAR (Phase 5).
- `app_android/app/src/main/res/mipmap-*/` – placeholder launcher icons so app builds.

**Requests to other tracks (open)**
- Track A: Need `models/vision_v1.pte` + `models/vision_v1.json` sidecar + `test_vectors/vision/` to build `ExecuTorchVisionEngine` (Phase 5.3).
- Track B: When Llama integration is needed in-app, the ExecuTorch 1.6.0 AAR must be placed in `app_android/app/libs/`. Confirm the correct AAR download URL for 1.6.0.

**Next steps**
1. Phase 5.1: Download ExecuTorch 1.6.0 AAR → place in `app_android/app/libs/` → uncomment line in `build.gradle.kts`.
2. Phase 5.3: `ExecuTorchVisionEngine.kt` — awaiting Track A `vision_v1.pte`.
3. Phase 5.4: `ExecuTorchAdvisoryEngine.kt` using `LlmModule`, `LlmCallback`, `LlmGenerationConfig`.
4. Phase 5.5: Wire `ClarificationEngine` and `AdvisoryPipeline` into the main scan flow; implement all failure-path screens.
5. Phase 5.7: Set `USE_MOCKS=false` in release build after real engines pass on-device test vectors.

### Session 2026-11-19 22:55 | agent: antigravity | branch: integration
Task IDs: C2, C7, Checkpoint 1

**Summary**
Built and deployed ExecuTorch LlamaDemo APK to the connected device (`00045345M000744`), loaded `llama32_1b.pte` and `tokenizer.model`, and recorded live on-device benchmark metrics satisfying Checkpoint 1 (Milestone I1).

**Done** (with evidence)
- Successfully compiled `external/executorch-examples/llm/android/LlamaDemo` under JDK 21 and Android SDK Platform 35.
- Pushed `llama32_1b.pte` (821 MB) and `tokenizer.model` (2.0 MB) to `/data/local/tmp/llama/` and app files directory.
- Benchmarked on connected phone (Model `A142`, MediaTek Dimensity 7200 Pro, arm64-v8a, 8 GB RAM):
  - Model load time: 0.752s
  - Time to first token (TTFT): 367 ms
  - Decode speed: 15.27 tokens/sec
  - Total latency for 70 tokens: 4.95s
  - Resident set size (RSS): 1408.8 MiB
  - Confirmed 0 network calls and smooth UI response.

### Session 2026-11-18 00:32 | agent: antigravity | branch: track-c
Task IDs: C1, C3, C4, C5, C6, C9, C10, C11, C12

**Summary**
Constructed the Android app architecture (`app_android/`), engine interfaces, mock engines, Jetpack Compose UI screens (Language, Camera guide, Result Card, Advisory with Clarifications), offline Room database, offline speech engine, and benchmark runner.

**Done** (with evidence)
- Audited environment: Android SDK (35), Build Tools (35.0.0, 36.0.0), NDK (27.0.12077973), Java 21, ADB daemon verified.
- Confirmed zero network constraint in `AndroidManifest.xml` (no `INTERNET` permission declared).
- Implemented `Contracts.kt` with Contract 1 (`VisionResult`), Contract 2 (`AdvisoryRequest`), Contract 3 (`AdvisoryResponse`), and engine interfaces (`VisionEngine`, `AdvisoryEngine`, `SpeechEngine`).
- Implemented `MockVisionEngine` with 7 scenarios (Early Blight, Late Blight, Rice Blast, Pest, Healthy, OOD Unknown, and Blurry quality issues).
- Implemented `MockAdvisoryEngine` with token streaming simulation and clarification loop for ambiguous diagnoses.
- Implemented Jetpack Compose UI in `AppScreens.kt` and `MainActivity.kt` covering Language selection, Camera framing guide, Result card, and Advisory/TTS.
- Implemented `AppDatabase.kt` with Room `ScanRecord` entity for offline SQLite history.
- Implemented `AndroidSpeechEngine.kt` for local offline Text-To-Speech with Indic language routing.
- Implemented benchmark harness `benchmarks/benchmark_runner.py` and generated baseline measurements in `benchmarks/results.csv` | verified by: `python benchmarks/benchmark_runner.py` -> 10 iterations executed, latency and memory logged.

**In progress / not done**
- Integration of actual `.pte` binaries once Tracks A and B finalize model training and export on shared drives/LFS.

**Next steps**
1. Track A to deliver `vision_v1.pte` with test vectors.
2. Track B to deliver Llama 3.2 ExecuTorch export.
3. Test APK build on device with ADB.

**Decisions made**
- MinSdk 26, TargetSdk 35 with Jetpack Compose Material3 for modern, responsive UI.
- Mock engines provided so full UI and user interaction flows can be verified independently without waiting on model weights.

**Files touched**
- `app_android/settings.gradle.kts`
- `app_android/build.gradle.kts`
- `app_android/app/build.gradle.kts`
- `app_android/app/src/main/AndroidManifest.xml`
- `app_android/app/src/main/java/com/offlinecrop/assistant/engine/Contracts.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/engine/mock/MockVisionEngine.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/engine/mock/MockAdvisoryEngine.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/engine/speech/AndroidSpeechEngine.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/data/AppDatabase.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/ui/screens/AppScreens.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/MainActivity.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/CropAssistantApp.kt`
- `app_android/app/src/main/java/com/offlinecrop/assistant/engine/ContractComplianceTest.kt`
- `speech/README.md`
- `benchmarks/benchmark_runner.py`
- `benchmarks/results.csv`
- `docs/handoffs/track-c.md`

**How to verify**
- `python benchmarks/benchmark_runner.py` -> expect 10 iterations written to `benchmarks/results.csv`.
- Inspect `AndroidManifest.xml` -> ensure no `INTERNET` permission.

**Blockers**
- None. Ready for model `.pte` handoffs from Track A and Track B.

**Requests to other tracks**
- To Track A: `vision_v1.pte` export.
- To Track B: Llama 3.2 `advisory.pte` export.

**Assumptions / could not verify**
- Physical phone was not connected via USB during session (`adb devices` list empty). On-device tests will run as soon as a target phone is connected.

## Archive summary

(Compacted older sessions go here.)
