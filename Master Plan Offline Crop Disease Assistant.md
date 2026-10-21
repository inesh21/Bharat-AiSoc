# Master Plan: Offline Crop Disease Assistant

*On-device AI for crop disease and pest identification, severity grading and multilingual advisory. Llama 3.2 on ExecuTorch, Arm Android first.*

Team: Member A (Vision), Member B (Knowledge + Llama), Member C (App + Voice + Integration). Fill in names in section 3.

## 1. Goal and scope

**Goal:** a farmer photographs a leaf (or a pest) and, with no internet, gets: what it is, how severe it is, what to do now, how to prevent it, in their own language, in text and voice.

**Scope freeze (decide together in the first meeting, then do not change without all three agreeing):**

- Region: one region (example: one Indian state).
- Crops: 3 to 5 crops.
- Classes: about 15 to 30 (diseases, pests, healthy, unknown).
- Languages: 2 to 3 (English plus the regional language, plus Hindi if desired).
- Device: one Arm Android phone first. Raspberry Pi 5 is a stretch goal (section 9).
- Mandatory tech: Llama 3.2 1B/3B-Instruct on ExecuTorch for the advisory/reasoning component.

**Innovations we commit to (core):**

1. Structured hand-off: the vision model emits JSON, Llama never sees raw guesses.
2. Clarifying-question loop when the top two diagnoses are close.
3. Uncertainty handling: image quality check, unknown/out-of-distribution refusal, calibrated confidence.
4. Rules-engine safety layer for chemicals and doses (Llama explains, never decides).
5. Offline retrieval over a curated, region-specific knowledge base with source IDs.
6. Voice-first, local-language interface.
7. Severity from lesion area percentage (OpenCV or tiny segmentation net).

**Stretch:** LoRA fine-tuned Llama 1B; microclimate early warning on Pi; store-and-forward outbreak sharing; extension-worker batch mode.

## 2. System architecture

```
[Camera / Gallery]
      |
[Image quality check]  blur, brightness, leaf present?
      |
[Vision model]  crop + disease/pest top-3 + confidence + OOD flag      <- TRACK A
      |
[Severity module]  lesion area % -> mild / moderate / severe           <- TRACK A
      |
[Context builder]  vision JSON + region + language + growth stage      <- TRACK B (logic)
      |
[Clarifying-question loop]  only if top-2 close                        <- TRACK B logic, TRACK C UI
      |
[Knowledge layer]  structured lookup + retrieval + rules engine        <- TRACK B
      |
[Llama 3.2 on ExecuTorch]  structured advisory                         <- TRACK B (model), TRACK C (runtime in app)
      |
[Output validator]  sections present, chemicals/doses match rules      <- TRACK B
      |   (fail -> template fallback built from the knowledge base)
[Language layer]  Llama native (English/Hindi) or pre-translated slots <- TRACK B (content), TRACK C (UI strings)
      |
[UI + TTS]   [STT for questions]   [Local DB: history]                 <- TRACK C
```

**Three flows, one product:**

| Flow | Owner | Input | Output |
| --- | --- | --- | --- |
| Perception flow | A | Image | Vision JSON (contract 1) |
| Reasoning flow | B | Vision JSON + context | Advisory JSON (contract 2) |
| Interaction flow | C | User actions, voice, camera | Everything the farmer sees, hears and says; hosts both models on device |

**Runtime rule:** Track C owns running models inside the Android app. Tracks A and B deliver packaged model artifacts plus test vectors, and verify them on a laptop first.

**If a Hailo accelerator is added later (Pi stretch):** the vision model runs through HailoRT on the Hailo NPU, and Llama runs through ExecuTorch on the Pi Arm CPU. These are separate pipelines and must be shown as two separate boxes in the report.

## 3. Tracks

### Track A: Vision and Severity (Member A: \_\_\_\_\_\_\_\_)

**Mission:** turn an image into a trustworthy, calibrated, quantized prediction and a severity band.

**Tasks, in order**

1. Data: download datasets (PlantVillage, a field-condition set such as PlantDoc, IP102 for pests, Cassava or region-specific crop sets). Record licenses.
2. Build a unified taxonomy `crop__condition` and a `labels.json`. Share it with B and C on Day 2.
3. Clean: deduplicate (perceptual hash), remove corrupt files, fix labels.
4. Split by source or plant, not randomly per image, to avoid leakage. Keep a final test set locked.
5. Collect your own 100 to 300 real-world phone photos including non-leaf images for the "unknown" class.
6. Baseline model: MobileNetV3-Large or EfficientNet-Lite, 224 to 256 px, pretrained, freeze then fine-tune.
7. Augmentation for field conditions: crop, color jitter, blur, random backgrounds, cutout, mixup/cutmix.
8. Add "unknown" class plus OOD score (max-softmax or energy) and choose a threshold on validation data.
9. Calibration: temperature scaling; report Expected Calibration Error.
10. Image-quality checker (OpenCV): blur (variance of Laplacian), brightness, leaf-area presence. Output a list of issues.
11. Severity module: segment leaf, segment lesions, compute percentage, map to bands per crop. Validate on a small hand-labeled set.
12. Export: PyTorch -> `torch.export` -> ExecuTorch (XNNPACK) `.pte`, int8 post-training quantization with a 200 to 1000 image calibration set. Fall back to quantization-aware training if accuracy drops more than 2 points.
13. Verify the exported model against PyTorch outputs on 50 images; save these as test vectors.
14. Write the model card: input size, normalization, labels, metrics, thresholds, version.

**Deliverables**

- `vision/` training and evaluation code, reproducible with one command.
- `models/vision_vX.pte` plus `vision_vX.json` (labels, normalization, thresholds, severity bands).
- `test_vectors/vision/` with 50 images and expected outputs.
- Metrics: accuracy, macro-F1, per-class results, confusion matrix, field-only results, ECE, quantization drop.

**Definition of done:** macro-F1 target met on the field-style test set (agreed target, example 0.85); unknown images are refused; model under the agreed size; on-device output matches laptop output within tolerance.

**Stretch:** pest detection with a nano detector; nutrient deficiency classes; Hailo HEF compile for Pi.

### Track B: Knowledge, Rules and Llama (Member B: \_\_\_\_\_\_\_\_)

**Mission:** turn a diagnosis into safe, correct, grounded, multilingual advice using Llama 3.2 on ExecuTorch.

**Tasks, in order**

1. **Day 1 risk task:** request Llama 3.2 access (Hugging Face and Meta download page). Export stock Llama 3.2 1B-Instruct to a quantized `.pte` using the ExecuTorch Llama example for the installed version, and run it on the laptop. Share the working command and the file with C.
2. Knowledge base: for every class from `labels.json`, write one JSON entry (schema in section 4) from trusted public extension sources. Record source name and date per entry.
3. Rules engine `rules.yaml`: chemical names, doses, pre-harvest interval, protective gear, banned or restricted items for the region, "see extension officer" triggers. Have a domain source or expert check every chemical line.
4. Retrieval: deterministic lookup by crop and condition first; BM25 (or a small multilingual embedding model) only for free-form follow-up questions.
5. Clarifying questions: for each commonly confused disease pair, write 1 to 3 yes/no discriminating questions and how each answer re-weights the candidates (a small table, no model needed).
6. Prompt design: system prompt (role, "use only provided context", required sections, short sentences, no invented chemicals or doses, say so when unsure) and a fixed user template filled from vision JSON plus knowledge snippets.
7. Context budget: keep prompts to roughly 600 to 1200 tokens; set `max_seq_length` accordingly.
8. Output validator: required sections present; chemicals exist in the rules table; doses match; otherwise return the template fallback built directly from the knowledge base.
9. Language strategy: Llama generates directly for languages it supports (for example English, Hindi); for others use pre-translated knowledge entries and slot templates reviewed by a native speaker, or a separate small offline translation model (documented as its own component).
10. Evaluation set: 100 to 200 (vision JSON -> expected advice facts) cases and a checklist: correct diagnosis, severity-appropriate advice, consistent with the knowledge base, no unsafe dose, language quality.
11. Benchmark 1B vs 3B quality on the evaluation set (latency measured later by C on the phone).
12. Stretch: synthetic Q&A data, LoRA fine-tune of 1B, ablation against the untuned model.

**Deliverables**

- `knowledge/` JSON entries, `rules.yaml`, retrieval code, clarifying-question table.
- `llm/prompts/`, validator code, evaluation set and scripts.
- `models/llama32_1b_vX.pte` plus tokenizer and `llama_config.json` (max sequence length, quantization scheme, export command, ExecuTorch version).
- `test_vectors/llm/` with 30 prompts and reference outputs.

**Definition of done:** 100 percent of advisories pass the validator or fall back; zero invented chemicals in the evaluation set; required sections present in over 95 percent of outputs; native-speaker review of at least 20 outputs per language.

### Track C: App, Voice and Integration (Member C: \_\_\_\_\_\_\_\_)

**Mission:** a smooth offline Android app that hosts both models, speaks and listens in local languages, and holds the whole system together.

**Tasks, in order**

1. Day 1: set up Android Studio, SDK and the NDK version required by the ExecuTorch Android README; enable USB debugging on the phone; confirm `adb devices` works.
2. Build the ExecuTorch Android library and run the reference Llama demo app with a pre-exported Llama 3.2 1B `.pte`. Record time to first token, tokens per second, RAM and any crash. This is the baseline.
3. Create the project app with module boundaries: `VisionEngine`, `AdvisoryEngine`, `SpeechEngine`, `Repository` (interfaces in section 4).
4. Build the UI against **mock** engines first (canned JSON), so the UI is never blocked.
5. Screens: language picker -> camera with framing guide and quality hints -> result card (label, confidence, severity with color and icon) -> advisory (text and audio) -> clarifying questions (buttons and voice) -> history.
6. CameraX capture, image preprocessing identical to Track A (same size, normalization, color order). Mismatched preprocessing is the most common integration bug.
7. Integrate the vision `.pte` (from A) through ExecuTorch. Verify against A's test vectors on the phone.
8. Integrate the Llama `.pte` (from B). Run generation on a background thread and stream tokens to the UI. Unload the vision model while Llama generates if memory is tight.
9. Speech: offline STT (Whisper tiny/base via whisper.cpp, or Vosk or an Indic model) and offline TTS (Android offline voices, Piper, or an Indic TTS model). Verify early that a voice exists for each chosen language.
10. Storage: Room/SQLite for scan history and a sync queue (queue is used only in the stretch outbreak feature).
11. Offline proof: remove the `INTERNET` permission from the manifest, test in airplane mode and show it in the demo.
12. Benchmark harness: 10-run loops recording vision latency, LLM time to first token, tokens per second, total scan time, peak RAM, battery and temperature, saved to `benchmarks/results.csv`.
13. Own the demo video, the integration test plan, the APK build, and compile the final report.

**Deliverables**

- `app_android/` source and a signed APK.
- `benchmarks/` scripts and results.
- Integration test report; demo video; compiled technical report.

**Definition of done:** a full scan works in airplane mode on the phone, in under the agreed end-to-end time (example 15 s), without crashes over 50 consecutive scans.

## 4. Interface contracts (freeze by Day 3)

All three tracks code against these. Changes need all three to agree, bump `schema_version`, and update the mocks.

### Contract 1: Vision output (A -> B and C)

```json
{
  "schema_version": "1.0",
  "image_id": "uuid",
  "model_version": "vision_v1",
  "quality": { "ok": true, "issues": [] },
  "unknown": false,
  "crop": "tomato",
  "predictions": [
    { "label": "tomato__early_blight", "type": "disease", "confidence": 0.78 },
    { "label": "tomato__septoria_leaf_spot", "type": "disease", "confidence": 0.15 },
    { "label": "tomato__healthy", "type": "healthy", "confidence": 0.04 }
  ],
  "severity": { "percent": 18.4, "band": "moderate" }
}
```

`quality.issues` values: `blurry`, `too_dark`, `too_bright`, `no_leaf`. If `quality.ok` is false or `unknown` is true, the app asks for a better photo or says it cannot help; Llama is not called.

### Contract 2: Advisory request (C -> B)

```json
{
  "schema_version": "1.0",
  "vision": { },
  "region": "region_code",
  "language": "en | hi | ta",
  "growth_stage": "seedling | vegetative | flowering | fruiting | unknown",
  "answers": [ { "question_id": "q_underside_spots", "answer": "yes" } ]
}
```

### Contract 3: Advisory response (B -> C)

```json
{
  "schema_version": "1.0",
  "status": "final | needs_clarification",
  "clarification": {
    "question_id": "q_underside_spots",
    "text": "Are the spots also on the underside of the leaf?",
    "options": ["yes", "no", "not sure"]
  },
  "diagnosis": "...",
  "severity_band": "moderate",
  "actions_now": ["..."],
  "prevention": ["..."],
  "seek_help": false,
  "source_ids": ["kb:tomato__early_blight"],
  "used_fallback": false,
  "language": "ta",
  "text": "full text for display and TTS"
}
```

### Kotlin interfaces (C implements, A and B supply what is behind them)

```kotlin
interface VisionEngine { suspend fun analyze(bitmap: Bitmap): VisionResult }
interface AdvisoryEngine { fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse }
interface SpeechEngine { fun listen(lang: String): String; fun speak(text: String, lang: String) }
```

### Knowledge base entry schema (B)

```json
{
  "id": "tomato__early_blight",
  "crop": "tomato",
  "type": "disease",
  "symptoms": ["..."],
  "conditions_favoring": ["..."],
  "severity_actions": { "mild": ["..."], "moderate": ["..."], "severe": ["..."] },
  "organic_options": ["..."],
  "chemical_options": [{ "name": "...", "dose": "...", "phi_days": 0, "safety": "..." }],
  "prevention": ["..."],
  "regions": ["..."],
  "sources": ["..."]
}
```

### Shared artifacts

- `labels.json` (A owns): the single list of class IDs. Everyone uses these exact strings.
- `models/manifest.json` (each owner updates their entries): file name, version, SHA-256, input size, normalization, date, and the ExecuTorch version used to export.
- `test_vectors/` (A and B own): fixed inputs and expected outputs so C can check on-device behavior.

**Critical compatibility rule:** one ExecuTorch version across all three machines and the app. Pin it in `docs/versions.md` on Day 1. Models exported with a different version than the app runtime may not load.

## 5. Integration plan

Principle: **integrate early with fakes, then replace fakes with real parts.** No track waits for another.

| Milestone | What it means | Who | Exit check |
| --- | --- | --- | --- |
| I0 Contracts frozen | Section 4 agreed, mock JSON files committed in `mocks/` | All | Each member can run their part against mocks |
| I1 Runtime proven | Stock Llama 1B runs through ExecuTorch on laptop (B) and the reference app runs it on the phone (C) | B + C | TTFT and tok/s recorded; pinned versions agreed |
| I2 Vision on device | Track A `.pte` runs inside the app, matching test vectors | A + C | 50 of 50 test images match within tolerance |
| I3 Advisory on device | B's Llama `.pte` plus knowledge base runs in the app from a vision JSON | B + C | 30 test prompts produce valid, validated advisories |
| I4 End to end | Photo -> vision -> severity -> advisory -> TTS, in airplane mode | All | 20 real photos, no crash |
| I5 Voice and clarifications | STT questions, clarifying loop, second language | B + C | Loop works on 5 ambiguous photos |
| I6 Freeze and polish | Benchmarks, ablations, bug fixes, demo recording | All | Release candidate APK |

**Integration rules**

- Every handoff is a file in `models/` plus an entry in `manifest.json`, never a chat message.
- Preprocessing parameters live in the model JSON from A. C reads them; nobody hardcodes.
- When something breaks at an integration point, the receiving track first runs the sender's test vectors to decide whose side the bug is on.
- Memory plan on phone: vision model stays small; Llama loaded on demand; measure peak RAM at I3 and decide the 1B vs 3B final choice by measured numbers, not laptop speed.
- Failure paths are features: low quality -> retake prompt; unknown -> "cannot identify, consult extension officer"; validator failure -> template fallback. C builds a UI for each.

## 6. Timeline (4 weeks, adjust to the real deadline)

**Week 1: foundations**

- All: scope freeze, repo, pinned versions, contracts and mocks (I0).
- A: datasets downloaded, taxonomy and `labels.json`, baseline model trained on a subset.
- B: Llama access, stock 1B exported and running on laptop, first 5 knowledge entries as a format pilot.
- C: Android toolchain, reference Llama app on the phone, UI skeleton on mocks. I1 reached.

**Week 2: build the parts**

- A: full training, augmentation, unknown class, calibration, quality checker, first severity version.
- B: full knowledge base, rules engine, prompts, validator, first evaluation run.
- C: all screens on mocks, camera pipeline, vision integration (I2), speech engine prototype.

**Week 3: connect and harden**

- A: quantized export, test vectors, field-image evaluation, severity validation.
- B: language layer, clarifying-question table, 1B vs 3B quality comparison, optional fine-tune.
- C: Llama integration (I3), end to end (I4), benchmark harness, offline proof.

**Week 4: polish and deliver**

- All: voice and clarifications (I5), ablations, bug bash, freeze (I6).
- Report sections written by each owner, compiled by C.
- Demo video recorded, APK built, repository cleaned and documented.

## 7. Repository and workflow

```
crop-assistant/
  data/              (gitignored)
  vision/            Track A
  knowledge/         Track B
  llm/               Track B
  speech/            Track C
  app_android/       Track C
  app_pi/            stretch
  models/            .pte files via Git LFS or shared drive + manifest.json
  mocks/             contract JSON samples
  test_vectors/      vision/ and llm/
  benchmarks/        Track C
  docs/              report, diagrams, versions.md
  labels.json
```

- Branches: `main` stays working; each member works on `track-a/...`, `track-b/...`, `track-c/...` and opens pull requests reviewed by one other member.
- Large files (models, data) do not go in plain Git; use Git LFS or a shared drive and record hashes in `manifest.json`.
- Daily 10-minute sync: what finished, what blocks, what is needed from another track.
- Weekly 45-minute integration session ending in a recorded demo of the current milestone.
- Shared tracker (board) with one card per task above, tagged by milestone.

## 8. Evaluation and report plan

**Metrics to collect**

- Vision: accuracy, macro-F1, per-class, field-only subset, ECE, unknown-class rejection rate, quantization drop.
- Severity: error versus hand labels, band agreement.
- Advisory: validator pass rate, fallback rate, invented-chemical count (target zero), section compliance, native-speaker ratings.
- System on device: vision latency, LLM TTFT, tokens per second, total scan time, peak RAM, model sizes, battery per scan, temperature.

**Ablations**

- Vision only vs vision + Llama.
- With vs without retrieval.
- 1B vs 3B.
- Base vs fine-tuned (if done).
- With vs without guardrails and fallback.

**Report outline (owner in brackets)**

1. Abstract and problem (C)
2. Users and requirements (C)
3. System architecture, including the two separate pipelines if Hailo is used (all)
4. Data and vision model (A)
5. Severity estimation (A)
6. Knowledge base, rules engine and guardrails (B)
7. Llama deployment with ExecuTorch: quantization, export, runtime (B + C)
8. Multilingual and voice (B + C)
9. Results, benchmarks and ablations (all)
10. Limitations and ethics: misdiagnosis risk, chemical safety, dataset bias, language coverage (all)
11. Future work (all)
12. References and licenses (all)

**Demo video (3 to 5 minutes), led by C**

- 0:00 problem and farmer scenario (30 s)
- Architecture on one slide (30 s)
- Live demo in airplane mode: scan, result, voice advice in a local language (90 s)
- Clarifying questions and the "cannot identify" safe refusal (45 s)
- Benchmarks and results (30 s)
- Impact and future work (20 s)

## 9. Risks and stretch

| Risk | Owner | Mitigation |
| --- | --- | --- |
| Export or build problems with ExecuTorch | B + C | Start Day 1 with stock Llama 1B; pin one version; ask early in official channels |
| Great PlantVillage accuracy, weak field accuracy | A | Field augmentation, own photos, report field-only metrics |
| LLM invents doses or chemicals | B | Rules engine, validator, template fallback |
| Llama weak in the chosen regional language | B | Pre-translated slots or separate small translation model |
| Preprocessing mismatch between training and app | A + C | Parameters in model JSON; test vectors on device |
| Out of memory or slow on phone | C | Lazy loading, shorter context, 1B model, measure at I3 |
| One member blocked by another | All | Mocks and contracts; daily sync |
| Scope creep | All | Scope frozen in section 1; stretch only after I4 |
| Vision runtime choice (ExecuTorch vs another) blocks A | A + C | Decide by Day 3: ExecuTorch preferred for one runtime story; fallback ONNX Runtime or TFLite for vision only |

**Stretch goals, only after I4:** Raspberry Pi 5 build (vision on Hailo via HailoRT, Llama on CPU via ExecuTorch, documented as separate pipelines); microclimate early warning with a temperature/humidity sensor; store-and-forward outbreak sharing; extension-worker batch mode; LoRA fine-tuned Llama.

## 10. Master checklist

- [ ] Scope frozen and written (section 1)
- [ ] Llama 3.2 access approved
- [ ] ExecuTorch version pinned in `docs/versions.md`
- [ ] `labels.json` shared
- [ ] Contracts and mocks committed (I0)
- [ ] Stock Llama 1B runs on laptop and phone (I1)
- [ ] Vision `.pte` verified on phone (I2)
- [ ] Knowledge base and rules reviewed
- [ ] Llama advisory verified on phone (I3)
- [ ] End-to-end offline scan (I4)
- [ ] Voice and clarifying loop (I5)
- [ ] Benchmarks and ablations recorded
- [ ] Network permission removed, airplane-mode proof recorded
- [ ] Report, video, APK, README, licenses (I6)
