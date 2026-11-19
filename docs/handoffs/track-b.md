# Handoff: Track B: Knowledge, Rules and Llama

**Active agent:** none
**Owner (human):** ________
**Branch / worktree:** track-b/main  ->  ../crop-wt/track-b
**Task IDs:** B1 to B12 (see `docs/tracks/TRACK_B_LLM.md`)
**Last updated:** 2026-11-19

## Milestone status

| Milestone | Status | Evidence |
|---|---|---|
| I0 Contracts frozen | done | Rules engine, KB, and Contract 3 advisory pipeline implemented |
| I1 Runtime proven | done | Exported Llama 3.2 1B (8da4w_xnnpack) to `models/llama32_1b.pte`; verified on connected phone (15.27 t/s, TTFT: 367ms) |
| I2 Vision on device | in progress | |
| I3 Advisory on device | in progress | Advisory pipeline & fallback ready for ExecuTorch integration |
| I4 End to end offline | in progress | 100% offline knowledge retrieval and validation |
| I5 Voice and clarifications | in progress | Multi-language phrases and clarifying questions matrix defined |
| I6 Freeze and polish | not started | |

## Requests to other tracks (open)

- To Track A: Taxonomy with 19 classes fully covered in `knowledge/kb.json`. | CONTRACTS.md Section 6 | needed for I0 | status: done
- To Track C: Advisory pipeline produces Contract 3 responses. Clarification questions supported via `q_underside_spots`, `q_rings_vs_specks`, etc. | CONTRACTS.md Section 4 | needed for I3 | status: ready

## Requests from other tracks (handled)

- Handled request from Track A: Grounded all 19 taxonomy classes in `knowledge/kb.json` with accredited citations from ICAR, TNAU, and IRRI.

## Session log (newest first)

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
