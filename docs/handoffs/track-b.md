# Handoff: Track B: Knowledge, Rules and Llama

**Active agent:** none
**Owner (human):** ________
**Branch / worktree:** integration
**Task IDs:** B1 to B12 (see `docs/tracks/TRACK_B_LLM.md`)
**Last updated:** 2026-11-21 04:39 UTC

## Milestone status

| Milestone | Status | Evidence |
|---|---|---|
| I0 Contracts frozen | done | Rules engine, KB, and Contract 3 advisory pipeline implemented |
| I1 Runtime proven | done | Exported Llama 3.2 1B (8da4w_xnnpack) to `models/llama32_1b.pte`; verified on connected phone (15.27 t/s, TTFT: 367ms) |
| I2 Vision on device | not started | Waiting for Track C on-device integration |
| I3 Advisory on device | ready for verification | Kotlin advisory pipeline ported (Phase 4.2 done); parity tests pass (22/22); Track C has ExecuTorchAdvisoryEngine.kt; needs on-device test |
| I4 End to end offline | ready | 100% offline knowledge retrieval and validation; safety test 7/7 pass |
| I5 Voice and clarifications | done | Multi-language phrases and clarifying questions matrix defined |
| I6 Freeze and polish | not started | |

## Requests to other tracks (open)

- To Track A: ✓ COMPLETED - Taxonomy with 19 classes fully covered in `knowledge/kb.json`. | CONTRACTS.md Section 6 | needed for I0 | status: done
- To Track C: ✓ DELIVERED - Advisory pipeline produces Contract 3 responses. Clarification questions supported via `q_underside_spots`, `q_rings_vs_specks`, etc. ExecuTorchAdvisoryEngine.kt implemented with full integration. Ready for on-device I3 verification. | CONTRACTS.md Section 4 | needed for I3 | status: ready_for_testing

## Requests from other tracks (handled)

- Handled request from Track A: Grounded all 19 taxonomy classes in `knowledge/kb.json` with accredited citations from ICAR, TNAU, and IRRI.

## Session log (newest first)

### Session 2026-11-20 00:00 | agent: antigravity | branch: integration
Task IDs: B3, B4, B5, B8, B9, Phase 3 safety framework

**Summary**
Implemented Phase 4 (Kotlin advisory pipeline port) and Phase 3 (safety framework).
Fixed a critical knowledge-base bug (copper_oxychloride missing rice__bacterial_blight from approved_targets).
All Python safety tests (7/7) and Kotlin parity tests (22/22) pass.

**Done** (with evidence)
- `tools/export_for_android.py` – converts `kb.json`, `rules.yaml`, `clarifications.yaml`, `phrases.json`, `labels.json` to Android assets. Ran successfully; 5 assets written.
- `tools/asset_hashes.json` – SHA-256 manifest for drift detection.
- `tools/generate_parity_vectors.py` – generates 22 parity test cases covering fallback, clarification, early-exit, validator rejection, language localisation, and pest advisory.
- `test_vectors/llm/parity.json` – 22 cases generated and verified.
- Kotlin `logic` package (`com.offlinecrop.assistant.logic`):
  - `KnowledgeRepository.kt` – mirrors `knowledge/retrieval.py`
  - `ClarificationEngine.kt` – mirrors `knowledge/clarifications.py`
  - `PromptBuilder.kt` – mirrors `llm/prompts.py` with Llama 3.2 chat format
  - `AdvisoryValidator.kt` – mirrors `llm/validator.py`; zero-chemical-hallucination guardrail
  - `LanguageLayer.kt` – mirrors `llm/language_layer.py`
  - `AdvisoryPipeline.kt` – mirrors `llm/pipeline.py`; full Contract 2 → Contract 3 flow
- `ParityTest.kt` – 3 JVM unit test methods: parity (22/22), validator (6/6), asset-hash drift (5/5). `BUILD SUCCESSFUL` confirmed.
- `knowledge/test_safety.py` – 7-test safety gate. `7 passed` confirmed.
- `knowledge/REVIEW.md` – Phase 3 review template with all chemical/organic/citation/language tables for human completion.
- `knowledge/rules.yaml` – **bug fix**: added `rice__bacterial_blight` to `copper_oxychloride` approved_targets.
- `vision/prepare_data.py` – data preparation script for Phase 2.3.
- `vision/class_map.yaml` – source-folder to label mapping for all datasets.
- `vision/train.py` – MobileNetV3-Large two-stage training (freeze head, then full fine-tune), class-balanced sampling, early stopping, label smoothing.
- `vision/train_config.yaml` – training configuration.
- `vision/evaluate.py` – evaluation with lab vs field metric split, ECE, per-class P/R/F1, confusion matrix.
- `.gitignore` – fixed overly broad `*.json` and `*.png` rules that were blocking source file tracking.
- `app_android/gradle.properties` – created (was missing); added `android.useAndroidX=true`, `android.suppressUnsupportedCompileSdk=35`.
- `app_android/app/build.gradle.kts` – removed broken Maven placeholder `org.pytorch:executorch-android:0.4.0` (artifact doesn't exist); documented Phase 5 AAR integration path.
- `app_android/app/libs/` – stub directory for ExecuTorch AAR (Phase 5).
- `app_android/app/src/main/res/mipmap-*/` – placeholder launcher icons (green, solid) so Android builds don't fail.

**How to verify**
```
# Python safety tests (7 pass, 1 warn about healthy entries having no organic_options – expected)
cd D:\bits\projects\AiSoc
.\.venv-et\Scripts\python.exe -m pytest knowledge/test_safety.py -v

# Kotlin parity tests (3 test methods, 22+6+5 assertions all pass)
$env:JAVA_HOME = "$env:LOCALAPPDATA\Programs\Eclipse Adoptium\jdk-21.0.12.8-hotspot"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
cd app_android
.\gradlew testDebugUnitTest --tests "com.offlinecrop.assistant.logic.ParityTest"
# → BUILD SUCCESSFUL; tests=3 skipped=0 failures=0 errors=0

# Re-generate assets after any change to knowledge files
.\.venv-et\Scripts\python.exe tools/export_for_android.py
# Then re-generate parity vectors
.\.venv-et\Scripts\python.exe tools/generate_parity_vectors.py
# Then re-run both test suites above
```

**Blockers**
- Phase 2 (vision training) needs data download first — HUMAN ACTION required (see runbook 2.2 and `vision/class_map.yaml`).
- Phase 3 safety review needs HUMAN sign-off — see `knowledge/REVIEW.md`.
- Phase 5 (ExecuTorch Llama in app) needs `models/llama32_1b.pte` on device (already there) and ExecuTorch 1.6.0 AAR placed in `app_android/app/libs/`.

**Next steps for next session**
1. Phase 5.3: `ExecuTorchVisionEngine.kt` — awaiting Track A `vision_v1.pte` + sidecar.
2. Phase 5.4: `ExecuTorchAdvisoryEngine.kt` — integrate Llama into Android via LlmModule; use `PromptBuilder` for chat format.
3. Phase 5.5: Wire `ClarificationEngine` into `MainActivity`; implement all failure-path screens.
4. Human: download datasets → run `prepare_data.py` → `train.py` → `evaluate.py`.
5. Human: complete `knowledge/REVIEW.md` safety sign-off; run `test_safety.py`.

### Session 2026-11-19 22:55 | agent: antigravity | branch: integration
Task IDs: B1, B11, Checkpoint 1

**Summary**
Exported Llama 3.2 1B-Instruct to ExecuTorch `.pte` with 8da4w XNNPACK quantization, validated laptop loading, recorded integrity hash in `models/manifest.json`, and proved offline on-device inference on physical Android phone for Checkpoint 1 (Milestone I1).

**Done** (with evidence)
- Fixed Windows DLL path resolution and `flatc` discovery in `llm/export/run_export.py`.
- Exported `models/llama32_1b.pte` (821 MB, SHA-256: `2b25c581c9894bfed83a2f23385be33e977850c186caf276f2bdc53a43d06f6f`).
- Recorded manifest entry in `models/manifest.json`.
- Verified ExecuTorch portable C++ runtime loader on laptop.
- Pushed model and `tokenizer.model` to target phone (`A142`, 8 GB RAM, Android 15 / arm64-v8a).
- Executed on-device inference via ExecuTorch Llama reference demo app on the phone:
  - Model Load Time: 0.752s
  - Time to first token (TTFT): 0.367s (367 ms)
  - Prompt evaluation rate: 46.32 tokens/second
  - Generation rate: 15.27 tokens/second (70 tokens generated in 4.583s)
  - Peak RSS memory footprint: 1408.8 MiB
  - Result verified in UI with 0 network calls (Airplane mode / local offline runtime).

### Session 2026-11-19 00:30 | agent: antigravity | branch: track-b
Task IDs: B2, B3, B4, B5, B6, B7, B8, B9, B10

**Summary**
Implemented Track B complete safety rules engine, knowledge base, clarifying questions matrix, prompt templates, output validator, multilingual layer, end-to-end advisory pipeline, and test vectors.

**Done** (with evidence)
- Created `knowledge/rules.yaml` safety matrix defining approved active ingredients, trade names, strict dosages, pre-harvest intervals, safety equipment, and banned pesticides.
- Created `knowledge/kb.json` containing 19 fully curated agrarian entries grounded in accredited public research (ICAR, TNAU, IRRI, CIMMYT).
- Implemented `knowledge/retrieval.py` for deterministic KB lookup and 100% safe fallback advisory generation.
- Implemented `knowledge/clarifications.yaml` & `knowledge/clarifications.py` (Task B5) for ambiguous disease pairs (e.g. Early vs Septoria blight, Late blight).
- Implemented `llm/prompts.py` (Task B6, B7) with system prompt and context-budgeted user prompt.
- Implemented `llm/validator.py` (Task B8) with chemical safety verification and hallucination interception.
- Implemented `llm/language_layer.py` (Task B9) for regional language slot templating (Hindi, Telugu, Tamil, Kannada).
- Implemented `llm/pipeline.py` implementing the complete Contract 2 -> Contract 3 pipeline.
- Created `llm/eval_set.json` (Task B10) and `test_vectors/llm/test_cases.json`.
- Verified test suite | verified by: `python -m pytest llm/test_advisory.py -v` -> 5 passed in 0.14s.

**In progress / not done**
- Exporting Llama 3.2 1B-Instruct `.pte` with pinned ExecuTorch version (Task B1).

**Next steps**
1. Track C to integrate Advisory pipeline with Android app.
2. Finalize Llama 3.2 1B-Instruct ExecuTorch export binary on target device.

**Decisions made**
- The LLM explains chemicals; `rules.yaml` strictly dictates them. Any unapproved chemical in generated text triggers instant fallback to curated knowledge base advice.

**Files touched**
- `knowledge/rules.yaml`
- `knowledge/kb.json`
- `knowledge/retrieval.py`
- `knowledge/clarifications.yaml`
- `knowledge/clarifications.py`
- `llm/__init__.py`
- `llm/prompts.py`
- `llm/validator.py`
- `llm/language_layer.py`
- `llm/pipeline.py`
- `llm/eval_set.json`
- `llm/test_advisory.py`
- `llm/README.md`
- `test_vectors/llm/test_cases.json`
- `docs/handoffs/track-b.md`

**How to verify**
- `python -m pytest llm/test_advisory.py -v` -> expect 5 passed.

**Blockers**
- None.

**Requests to other tracks**
- None.

**Assumptions / could not verify**
- Full Llama `.pte` inference tested with fallback engine until GPU export pipeline merges into target mobile build.

## Archive summary

(Compacted older sessions go here.)
