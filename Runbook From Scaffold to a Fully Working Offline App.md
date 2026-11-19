# Runbook: From Scaffold to a Fully Working Offline App

*Step-by-step, phase by phase, starting from the current state of the codebase (all three tracks merged to main, models not yet trained or exported, nothing yet run on a phone).*

## 0. How to use this runbook

- Do **one phase at a time**. Every phase ends with a **Checkpoint**: a command or test whose result you write into your track's handoff file. Do not start the next phase until the checkpoint passes.
- Commands for ExecuTorch were checked against the ExecuTorch documentation (main branch, which lists version 1.4.0 on Maven Central). Versions move quickly, so pin one version (Phase 0) and use it everywhere.
- Where a step says *human*, an AI agent must not do it alone (safety content, real photos, device work).
- Rough effort is given per phase for a 3-person team; adjust to your deadline.

**What exists today:** Python code for vision (untrained), knowledge base, rules, validator, prompts; a Kotlin app running on mock engines. **What does not exist yet:** a trained vision model, a Llama `.pte` running on a phone, a build recorded on a real device, Kotlin versions of the Python logic, speech-to-text, real benchmarks.

---

## Phase 0: Audit and clean up (Day 1, all three)

### 0.1 Branches

1. In the repo run `git branch -a` and `git status`. The handoffs say branches `track-a`, `track-b`, `track-c`. Git cannot hold both `track-a` and `track-a/main`, so keep the plain names.
2. Create the integration branch from main:

   ```
   git switch main
   git switch -c integration
   ```
3. From now on: work on `track-x`, merge into `integration` when tested, merge `integration` into `main` only at milestones.

### 0.2 Run every existing test in a clean environment

```
python -m venv .venv-test
.venv-test/Scripts/activate      # Windows; on Linux/macOS: source .venv-test/bin/activate
pip install -r requirements.txt  # if missing, create it from the imports
pytest vision llm
```

Then the Android build:

```
cd app_android
./gradlew assembleDebug testDebugUnitTest lint
```

Write down every failure. Fix compile errors first.

### 0.3 Fix known problems

1. `app_android/.../engine/ContractComplianceTest.kt` is inside `src/main`. Move it to `app/src/test/java/...` so it runs with `gradle test` and does not ship in the APK.
2. Make sure release builds cannot use mock engines. Add a Gradle build flag, for example `buildConfigField('boolean', 'USE_MOCKS', 'true')` for debug and `'false'` for release, and choose engines from it.
3. `benchmarks/results.csv` came from a Python script with no phone attached. Rename it `benchmarks/laptop_mock_results.csv` and never quote it as phone data.
4. Correct each handoff's milestone table so a row says *done* only when its exit check was run (see `HANDOFF.md` section 8). I0 is *done* only after Phase 0 and the contract check below pass.

### 0.4 Contract check with real data

1. Run Track A's pipeline on 5 sample images and save the JSON outputs to `mocks/vision_*.json`.
2. Feed them to Track B: `python -c` or a small test that calls `llm/pipeline.py` with each, and save the responses to `mocks/advisory_*.json`.
3. In Track C, parse those same files with the Kotlin data classes in a unit test. Fix any field-name, null, or enum mismatch (for example `severity` can be null, band `none`).

### 0.5 Pin versions and decisions

1. Python: ExecuTorch wheels support specific Python versions. Track A used Python 3.14, which may not be supported. Create a **separate venv with Python 3.11 or 3.12** for all export work and check the Python versions listed on PyPI for `executorch`.
2. Fill `docs/versions.md`: ExecuTorch version (example 1.4.0), matching PyTorch, Python, Android SDK/NDK, target phone.
3. Fill ADR 0002 (scope): final crops, classes, languages. **Recommendation: English plus one regional language (and optionally Hindi), not four.** Remove translations nobody can review.
4. Fill ADR 0001 (vision runtime): ExecuTorch for vision too (this runbook assumes it).

**Checkpoint 0:** all tests pass (or failures are logged), integration branch exists, versions pinned, scope frozen, mocks round-trip through all three tracks.

---

## Phase 1: Get Llama running (Days 1 to 4, Track B and Track C)

This is the highest-risk item. Do it before anything else.

### 1.1 Request access (Track B human, now)

1. Hugging Face: open `meta-llama/Llama-3.2-1B-Instruct` and accept the license.
2. Meta: request the download at the Llama downloads page (you get the `consolidated.00.pth`, `params.json`, and `tokenizer.model` files, or download `original/` from the Hugging Face repo).
3. Approval can take hours. While waiting, do 1.2 and 1.4 using the fast path in 1.3.

### 1.2 Install ExecuTorch in the export environment (Track B)

```
python3.11 -m venv .venv-et
source .venv-et/bin/activate        # Windows: .venv-et\Scripts\activate
pip install executorch pytorch-tokenizers
pip show executorch                 # note the version, put it in docs/versions.md
```

Linux or macOS (or WSL2 on Windows) is the smoothest for export. If a command fails, read the ExecuTorch Getting Started page for your platform.

### 1.3 Fast path to unblock Track C (optional, 30 minutes)

A community export of Llama 3.2 1B Instruct for ExecuTorch 1.4.0 exists on Hugging Face (`experimentalmachines/Llama-3.2-1B-Instruct-ExecuTorch`, XNNPACK, 8da4w, 2k window, about 0.96 GB). Use it **only to test the app plumbing**. It is a third-party upload, so do your own export (1.4) for the final project and respect the Llama license terms.

### 1.4 Export the stock Llama 3.2 1B yourself (Track B)

1. Put `consolidated.00.pth`, `params.json`, `tokenizer.model` in `models_src/llama32_1b/` (gitignored).
2. Create `llm/export/llama32_1b_xnnpack.yaml`:

   ```
   base:
     model_class: llama3_2
     checkpoint: models_src/llama32_1b/consolidated.00.pth
     params: models_src/llama32_1b/params.json
     metadata: '{"get_bos_id":128000, "get_eos_ids":[128009, 128001]}'
   model:
     use_kv_cache: True
     use_sdpa_with_kv_cache: True
   quantization:
     embedding_quantize: 4,32
     qmode: 8da4w
     group_size: 32
   backend:
     xnnpack:
       enabled: True
       extended_ops: True
   ```
3. Run:

   ```
   python -m executorch.extension.llm.export.export_llm --config llm/export/llama32_1b_xnnpack.yaml
   ```
4. The output is a `.pte` (about 1 GB). Set the context length in the `export:` section (`max_seq_length`, `max_context_length`; see `LlmConfig` in the ExecuTorch repo if the names differ in your version). Start with 2048. The KV cache is allocated when the model loads, roughly 128 MB for 2048 tokens on the 1B model.
5. If the answers are poor, try 8-bit embeddings or a larger group size. Re-test.
6. Record the exact command, YAML and ExecuTorch version in `docs/versions.md`.

### 1.5 Run it on the laptop (Track B)

Follow the *Running LLMs with C++* page of the ExecuTorch docs to build the runner, or test directly on the phone in 1.7 (the phone test is the one that matters). Ask the model one agriculture question and confirm it answers sensibly.

### 1.6 Prepare the phone (Track C human)

1. Phone: Settings -> About -> tap Build number 7 times -> Developer options -> enable USB debugging.
2. PC: install Android Studio and platform-tools. Check the cable and run `adb devices`: the phone must show as `device`, not `unauthorized`.
3. Install the SDK and NDK versions your project and the ExecuTorch Android docs need (your handoff reports SDK 35, NDK 27.0.12077973).

### 1.7 Reference demo on the phone (Track C)

1. Clone `meta-pytorch/executorch-examples` and open `llm/android/LlamaDemo` in Android Studio (the demo moved there from the main ExecuTorch repo).
2. Copy the `.pte` and `tokenizer.model` to the phone:

   ```
   adb shell mkdir -p /data/local/tmp/llama
   adb push llama32_1b.pte /data/local/tmp/llama/
   adb push tokenizer.model /data/local/tmp/llama/
   ```
3. Run the demo, select the model and tokenizer in its settings (follow its README), and send a prompt.
4. Record in the handoff: phone model, RAM, time to first token, tokens per second (the app shows or logs them), any crash. This is the **real I1 evidence**.

**Checkpoint 1:** stock Llama 1B answers a prompt on the phone with no internet; numbers recorded; export command saved; `.pte` and tokenizer in `models/` with a manifest entry (SHA-256).

---

## Phase 2: Make the vision model real (Days 2 to 12, Track A)

Track A's files cover the model, quality check, severity, calibration and export, but there is no training or evaluation script and no data. Do these in order.

### 2.1 Environment

Keep the GPU training environment (your PyTorch with CUDA) separate from the export environment from 1.2. Train in the first, export in the second if package versions conflict (copy only the saved weights between them).

### 2.2 Data (human downloads)

1. Download datasets that cover your 19 classes: PlantVillage (tomato, potato, maize), a rice leaf disease dataset, a cotton leaf disease dataset, an IP102 subset or another dataset for fall armyworm, and PlantDoc for field-style images of tomato, potato, and maize. Search Kaggle and Hugging Face for each name and read each license before use.
2. Put them in `data/raw/<source_name>/`. Add each to `docs/DATASETS.md` with URL, license, class mapping.
3. Write `vision/prepare_data.py` that maps source folders to your `crop__condition` labels using a `class_map.yaml`, removes corrupt files, removes near-duplicates (perceptual hash, already in `dataset.py`), and writes `data/processed/manifest.csv` with columns: `path,label,source,split`.

### 2.3 Splits that do not leak

- `test`: the **field-style** data (your own photos and PlantDoc images). Lock it. Never tune on it.
- `train` and `val`: PlantVillage and the other lab-style sets, with `val` taken from different source folders or plants than `train`, never random images of the same leaf.
- Add an `unknown` class: 300 to 1000 non-plant images (soil, hands, random objects, other plants), also split by source.

### 2.3b Your own photos (human, highest value task)

Take at least 15 to 20 photos per class when you can find the real thing: gardens, fields, agricultural college plots, markets. Different light, backgrounds, distances. Label and store them under `data/raw/own_field/` and use them for `test`. If you cannot find real diseased plants for some class, say so in the report and treat that class as lab-only.

### 2.4 Write the training and evaluation scripts

Ask the agent for `vision/train.py` and `vision/evaluate.py` with:

- MobileNetV3 (ImageNet weights), 224x224 input, normalization from `vision/model.py` (must match the sidecar later).
- Stage 1: freeze backbone, train the head 3 epochs. Stage 2: unfreeze, fine-tune 15 to 30 epochs with AdamW, cosine schedule, label smoothing 0.1, class-balanced sampling, early stopping on validation macro-F1.
- Augmentation from `dataset.py` (crop, color jitter, blur, random background, cutout).
- `evaluate.py` printing accuracy, macro-F1, per-class precision/recall, confusion matrix image, ECE, and reporting **field-test metrics separately from lab metrics**.
- Logs to `vision/runs/<date>/` (gitignored), best weights saved to `models_src/vision_v1.pt`.

Run training first on 2 or 3 classes for a quick sanity run (a few minutes), then the full set.

### 2.5 Calibration and unknown threshold

1. Fit temperature on `val` using `calibration.py`. Record the temperature and ECE.
2. Pick the unknown threshold: compute the energy (or max-softmax) score on validation known images and on unknown images; choose the threshold that keeps at least 90 to 95 percent of known images while rejecting as many unknown as possible. Write it to the sidecar JSON, not into code.

### 2.5b Severity validation

Hand-label (or visually grade) 30 leaves as mild/moderate/severe, run `severity.py`, and report agreement. If it is poor, tune the segmentation thresholds per crop. Be honest in the report that severity is an estimate.

### 2.6 Iterate

Expect the first field-test score to be much lower than the lab score. Look at the confusion matrix, add field-like augmentation and more field data for the weak classes, and retrain. Stop when you meet the target agreed in ADR 0002, or document the real number.

### 2.7 Export to ExecuTorch (export environment)

Start with **float32** so you have a working `.pte` early, then quantize.

```
import torch
from executorch.exir import to_edge_transform_and_lower
from executorch.backends.xnnpack.partition.xnnpack_partitioner import XnnpackPartitioner

model = load_model('models_src/vision_v1.pt').eval()   # your model class and weights
example = (torch.randn(1, 3, 224, 224),)
ep = torch.export.export(model, example)
et = to_edge_transform_and_lower(ep, partitioner=[XnnpackPartitioner()]).to_executorch()
open('models/vision_v1.pte', 'wb').write(et.buffer)
```

Then quantize to int8 using the quantization guide linked from the ExecuTorch docs (PT2E post-training quantization with a calibration set of 200 to 1000 training images). Re-evaluate; if accuracy drops more than 2 points, try quantization-aware training or keep fp32 (MobileNetV3 is small enough for a phone).

The model must output **raw logits**. Temperature scaling and softmax are applied in the app using the sidecar value.

### 2.8 Verify the `.pte` on the laptop

Use the ExecuTorch Python runtime (see the Runtime Python API reference in the docs) to run the exported file and compare with PyTorch:

```
from executorch.runtime import Runtime
prog = Runtime.get().load_program('models/vision_v1.pte')
method = prog.load_method('forward')
out = method.execute([tensor])      # tensor shaped 1x3x224x224
```

On 50 test images the logits must match PyTorch within the tolerance you choose (for example max absolute difference 1e-3 for fp32).

### 2.9 Test vectors and sidecar

1. `test_vectors/vision/` holds the 50 preprocessed input tensors or images, and `expected.json` with the logits and final Contract 1 output for each.
2. `models/vision_v1.json` (sidecar): input size, channel order, normalization, temperature, unknown threshold, severity bands, label file, tolerance (schema in `docs/CONTRACTS.md` section 7).
3. Add the manifest entry with SHA-256 (`certutil -hashfile file SHA256` on Windows, `sha256sum` on Linux).
4. Share the `.pte` through the team drive or Git LFS, not plain git.

**Checkpoint 2:** metrics table (lab and field) in the handoff; `.pte` matches PyTorch on 50 images; sidecar and manifest committed.

---

## Phase 3: Verify the safety content (Days 3 to 10, humans, in parallel)

An agent produced `knowledge/rules.yaml` and `knowledge/kb.json`. Treat them as a draft.

1. **Chemicals and doses (`rules.yaml`):** for every active ingredient, find the dose and pre-harvest interval on an official label or an official extension source for your region (agricultural university, state agriculture department, national plant protection registry). Add a `verified_by` and `source_url` field next to each line. Anything you cannot confirm: delete the dose and mark `verified: false`. The advisory must then say to consult an extension officer for chemical options.
2. **Banned or restricted products:** check your country and state lists. Remove any product that is restricted for the crop.
3. **`kb.json`:** open each cited source and check it exists and supports the claim. Spot-check at least 30 percent of entries; do all high-risk ones (chemical advice). Fix or remove invented citations.
4. **Organic and cultural steps first:** make sure severity-based actions start with removal, sanitation, resistant varieties, spacing, and only then chemicals.
5. **Language review:** a native speaker reviews every phrase of every language you keep. Remove languages without a reviewer.
6. Add a test that fails if any chemical in `kb.json` is missing from `rules.yaml` or has `verified: false` while still appearing in an advisory.

**Checkpoint 3:** a short review log (who checked what, when) committed in `knowledge/REVIEW.md`; the safety test passes.

---

## Phase 4: Make the logic run on the phone (Days 8 to 16, Track B with Track C)

Python does not run inside the Android app. Only the model files do. The rest of the pipeline must be ported to Kotlin. Keep the Python code as the **reference** and prove the Kotlin version matches it.

### 4.1 Export data files for the app

Create `tools/export_for_android.py` that converts `rules.yaml`, `clarifications.yaml`, `kb.json`, language phrases and `labels.json` to JSON files in `app_android/app/src/main/assets/` (`kb.json`, `rules.json`, `clarifications.json`, `phrases.json`, `labels.json`). Run it whenever the sources change. Keep the app and Python from drifting by adding a hash check to a unit test.

### 4.2 Port these pieces to Kotlin (package `com.offlinecrop.assistant.logic`)

| Python source | Kotlin class | Notes |
| --- | --- | --- |
| `knowledge/retrieval.py` | `KnowledgeRepository` | lookup by crop and condition, fallback advisory builder |
| `knowledge/clarifications.py` | `ClarificationEngine` | pick question, re-weight top candidates from answers |
| `llm/prompts.py` | `PromptBuilder` | builds the system and user text |
| `llm/validator.py` | `AdvisoryValidator` | sections present, chemicals and doses exist in rules |
| `llm/language_layer.py` | `LanguageLayer` | slot templates and phrases |
| `llm/pipeline.py` | `AdvisoryPipeline` | the Contract 2 -> Contract 3 flow |
| `vision/quality.py` | `ImageQualityChecker` | see 4.3 |
| `vision/severity.py` | `SeverityEstimator` | see 4.3 |

Use `kotlinx.serialization` for JSON. Keep each class free of Android dependencies so it can be tested on the laptop JVM.

### 4.3 Image quality and severity in Kotlin

Downscale the bitmap to about 256 px on the long side, convert to grayscale, and compute blur (variance of a Laplacian filter), brightness (mean) and leaf presence (fraction of green-hue pixels in HSV) with plain loops. This avoids bundling OpenCV. (OpenCV for Android is available if you prefer, but it adds size and setup.) Port the lesion segmentation thresholds from `severity.py` the same way. Check parity on 20 images; small differences are expected, so set a tolerance (for example severity percent within 3 points) and record it.

### 4.4 Parity tests (the key safety net)

1. Python writes `test_vectors/llm/parity.json`: for each of 30 or more cases, the Contract 2 input, the expected fallback Contract 3 output, the expected prompt string, and the validator verdict for a set of fake model outputs (good, missing section, invented chemical, wrong dose).
2. Kotlin JVM unit tests read the same file and assert identical results.
3. Run them in CI on every change: `./gradlew testDebugUnitTest`.

**Checkpoint 4:** the Kotlin advisory pipeline in fallback mode (no Llama) reproduces all Python parity cases; no network or Python needed.

---

## Phase 5: Put the models inside the app (Days 12 to 22, Track C)

### 5.1 Add ExecuTorch to the app

In `app/build.gradle.kts` add the AAR with the **same version** as the Python package you exported with (check `pip show executorch`):

```
dependencies {
    implementation("org.pytorch:executorch-android:1.4.0")
}
```

Build once and confirm the APK size is still reasonable. Use only the `arm64-v8a` ABI for the release to keep it small (`ndk { abiFilters += listOf("arm64-v8a") }`).

### 5.2 Model files

The `.pte` files are large (about 1 GB for Llama). Do not put the Llama file in the APK. Options: copy it to `/sdcard/Android/data/<package>/files/models/` with `adb push` during development, and document a one-time model copy for the demo (or use an Android asset pack for a polished release). Load by absolute path.

### 5.3 `ExecuTorchVisionEngine`

1. Load the model with `Module.load(path)` (once, on a background thread).
2. Read `vision_v1.json` and `labels.json` from assets or the models folder. Never hardcode size, mean or std.
3. Preprocess: resize to the sidecar size, convert to RGB floats, normalize with mean and std, arrange as channels-first (NCHW) in a FloatArray.
4. Run: `Tensor.fromBlob(floats, longArrayOf(1, 3, 224, 224))`, `module.forward(EValue.from(tensor))`, then `outputs[0].toTensor().dataAsFloatArray` gives the logits.
5. Apply temperature and softmax, compute the energy score, apply the unknown threshold, pick the top 3, run quality and severity, and assemble the Contract 1 object.
6. Verify with the 50 test vectors on the phone (an instrumented test or a hidden debug screen). Pass criterion: logits within the sidecar tolerance.

### 5.4 `ExecuTorchAdvisoryEngine`

1. Create the module with `LlmModule(modelPath, tokenizerPath, temperature)` (use a low temperature such as 0.2 to 0.4 for advice), call `load()` once, and check that it returns 0.
2. Build the prompt with `PromptBuilder` using the **Llama 3.2 chat format**. A prompt looks like this (real line breaks, not the characters backslash-n):

   ```
   <|start_header_id|>system<|end_header_id|>
   
   SYSTEM TEXT<|eot_id|><|start_header_id|>user<|end_header_id|>
   
   USER TEXT<|eot_id|><|start_header_id|>assistant<|end_header_id|>
   
   ```

   The runner may add the beginning-of-text token itself. Test once with and without `<|begin_of_text|>` and keep whichever does not produce a doubled token or garbage.
3. Generate **off the main thread** with a callback implementing `LlmCallback` (`onResult(token)`, `onStats(json)`, `onError(code, message)`). Use `LlmGenerationConfig.create().seqLen(...).echo(false).build()` to limit length. Collect tokens into a StringBuilder and push them to the UI.
4. Call `module.resetContext()` before each new scan so old prompts do not stay in the cache.
5. When generation ends, parse the text into the required sections, run `AdvisoryValidator`, and if it fails use the template fallback and set `used_fallback = true`.
6. Save the stats JSON (time to first token, tokens per second) for the benchmark.
7. Provide a stop button that calls `module.stop()`.

### 5.5 Clarification loop and failure paths

Wire `ClarificationEngine` between vision and advisory. Make sure every row of the failure table in `docs/ARCHITECTURE.md` section 5 has a screen: bad quality, unknown, model load failure, out of memory, validator fallback.

### 5.6 Memory

Load vision at start, load Llama only when needed, and call `module.stop()` and release references when leaving the screen. If the phone struggles, unload vision while Llama runs. Test on the real phone with `adb shell dumpsys meminfo <package>`.

### 5.7 Replace mocks

Set `USE_MOCKS=false` for the release build. Keep mocks only for UI tests.

**Checkpoint 5 (I2, I3, I4):** vision test vectors pass on the phone; 30 advisory parity prompts run through the real Llama and are accepted or safely fall back; a full photo-to-advice scan works in airplane mode.

---

## Phase 6: Voice (Days 14 to 24, Track C, with help from Track B)

### 6.1 Text-to-speech

1. Android system TTS: install the offline voice data for each language on the test phone (Settings -> Language -> Text-to-speech output). Check each voice actually works in airplane mode.
2. Be honest in your docs: voice data is a **one-time device setup**. The app itself makes no network calls.
3. If a voice is missing or poor for your regional language, use a bundled engine (Piper or sherpa-onnx voices) as a fallback, or show text with a recorded-audio set for the most common advice.

### 6.2 Speech-to-text

Pick one and test it in airplane mode with real accents and background noise:

- **Vosk** (small offline models; check the model list for your language).
- **whisper.cpp** (multilingual, bigger and slower; needs a JNI build).
- **Android SpeechRecognizer** with offline language packs installed on the device.

Use speech-to-text only for short inputs: answering clarifying questions (yes/no/not sure) and picking the language. Short answers are far more reliable than free dictation. Offer buttons as the backup input.

### 6.3 Language QA

Native speakers listen to the 20 most common advisories in each language and mark errors. Fix the phrase files, not the model.

**Checkpoint 6 (I5):** the clarifying loop works by voice and by buttons on 5 ambiguous photos, with audio in each supported language.

---

## Phase 7: Prove it is offline, measure it, harden it (Days 22 to 28)

### 7.1 Offline proof

1. Build a release: `./gradlew assembleRelease`.
2. List the permissions: `apkanalyzer manifest permissions app-release.apk` (or `aapt dump permissions`). `INTERNET` must not appear. Libraries can add it when manifests merge, so check the merged result.
3. Put the phone in airplane mode, remove the SIM and Wi-Fi, and run a scan. Record the screen.

### 7.2 Real benchmarks

Add a hidden Benchmark screen to the app that runs 10 consecutive scans on fixed test images and writes a CSV to the app files folder, then `adb pull` it. Record: vision latency, Llama time to first token and tokens per second (from `onStats`), total scan time, peak memory (`dumpsys meminfo`), battery drop and temperature (`BatteryManager` or `dumpsys battery`). Close other apps, use the same battery level and brightness, and note the phone model and OS.

### 7.3 1B or 3B

Repeat Phase 1.4 for Llama 3.2 3B (same YAML, 3B files). Compare quality on Track B's evaluation set and speed on the phone. Keep 1B if 3B is too slow or large.

### 7.4 Stability

50 consecutive scans without a crash; rotate the screen; background and resume the app; deny the camera permission and recover; fill storage nearly full; test with a low battery. Fix what breaks.

### 7.5 Ablations for the report

Vision only vs vision plus Llama; with vs without the validator; fallback vs Llama text quality; 1B vs 3B. Each is a table of numbers you measured.

**Checkpoint 7 (I6):** release APK, airplane-mode recording, `benchmarks/phone_results.csv` with real data, 50-scan stability log.

---

## Phase 8: Deliverables (Days 26 to 30, all)

1. **Source code:** clean README (setup, model download, build, run), licenses (Llama community license, dataset licenses), no secrets or weights in git.
2. **Application:** the APK and a one-page install guide (including copying model files).
3. **Technical report:** use the outline in the master plan. Include the architecture figure, the data and field-vs-lab results, severity validation, safety design (rules table, validator, fallback), ExecuTorch export details, benchmarks and ablations, limitations and ethics.
4. **Demo video (3 to 5 minutes):** problem and farmer scenario, architecture slide, live airplane-mode scan with voice advice, an unclear photo (clarifying question) and an unknown photo (safe refusal), benchmark numbers, impact.
5. If you add a Raspberry Pi build later: vision on the Hailo NPU through HailoRT, Llama on the Pi CPU through ExecuTorch, documented as two separate pipelines.

---

## Who does what, and when

| Days | Track A (vision) | Track B (Llama + knowledge) | Track C (app) |
| --- | --- | --- | --- |
| 1 | Phase 0 | Phase 0, request access | Phase 0, phone setup |
| 2 to 4 | Data download, splits | Phase 1 export | Phase 1 reference demo |
| 5 to 10 | Train, field photos | Phase 3 review, then Phase 4 exporter | Phase 4 port, UI polish |
| 10 to 16 | Calibrate, export, vectors | Parity tests, prompts for Llama | Phase 5 vision engine |
| 16 to 24 | Iterate on weak classes, severity | 3B vs 1B evaluation, language review | Phase 5 Llama engine, Phase 6 |
| 24 to 30 | Help with benchmarks and report | Ablations, report | Phase 7, 8 |

Track C carries the most risk. When Track A or B finishes early, they take speech prototypes, benchmark scripts and report sections.

---

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| `import executorch` fails or export errors on Python 3.14 | Use Python 3.11 or 3.12 in a separate venv |
| App crashes on model load | Model and AAR versions differ (re-export with the AAR's version or change the Gradle version), file path wrong, file permissions, out of memory |
| Llama output is garbage or repeats | Wrong chat template, doubled start token, wrong tokenizer file, temperature too high |
| Output stops mid-sentence | `seqLen` or `max_seq_length` too small |
| Vision results differ between laptop and phone | Normalization, channel order, or resize method differs; check the sidecar and compare the preprocessed tensors first |
| Vision very accurate on lab images, bad on photos | Domain gap: more field data and augmentation; report field-only metrics |
| Phone gets hot or slow | Fewer threads, shorter prompts, 1B model, let it cool between benchmark runs |
| `INTERNET` shows up in the release manifest | A dependency added it; remove with `tools:node="remove"` in your manifest and re-check |
| Gradle build errors after adding ExecuTorch | NDK or Gradle plugin mismatch; match the ExecuTorch Android docs and your pinned versions |

---

## Agent prompts per phase

Use the session start and end prompts from `docs/AGENT_PROMPTS.md`, then add the task line:

- **Phase 0:** "Do Phase 0 of the runbook only. Run all tests, fix the listed issues, and report failures you cannot fix. Do not add features."
- **Phase 1 (Track B):** "Do runbook steps 1.2 to 1.5. Use the ExecuTorch version pinned in docs/versions.md and the YAML in step 1.4. Record exact commands and errors. Do not invent flags."
- **Phase 2 (Track A):** "Write vision/prepare\_data.py, vision/train.py and vision/evaluate.py per runbook 2.2 to 2.5. Split by source, report field and lab metrics separately, and do not tune on the test split."
- **Phase 2 export (Track A):** "Do runbook 2.7 to 2.9: export to ExecuTorch, verify against PyTorch on 50 images, create test vectors, sidecar JSON and manifest entry."
- **Phase 3:** "Add the verified/source fields to rules.yaml and a test that blocks unverified chemicals. Do not fill in any dose yourself; leave unverified items flagged."
- **Phase 4 (Track B):** "Write tools/export\_for\_android.py and the parity.json generator per runbook 4.1 and 4.4."
- **Phase 4 (Track C):** "Port the listed Python classes to Kotlin (runbook 4.2) with JVM unit tests that read parity.json. Pure Kotlin, no Android dependencies in the logic package."
- **Phase 5 (Track C):** "Implement ExecuTorchVisionEngine and ExecuTorchAdvisoryEngine per runbook 5.3 and 5.4. Verify with test vectors on the phone. Report only what you actually ran."
- **Phase 7 (Track C):** "Implement the Benchmark screen and CSV export per runbook 7.2, and run the offline permission check in 7.1."
