# AGENTS.md: Offline Crop Disease Assistant

This is the single source of truth for every coding agent working in this repo (Codex, Antigravity, Claude Code, or any other). `CLAUDE.md` and `GEMINI.md` only point here. If you are an agent, read this whole file before doing anything.

## 1. Project in one paragraph

An on-device Android app (Arm) that lets a farmer photograph a leaf or pest and, with **no internet**, get: what it is, how severe it is, what to do now, how to prevent it, in their own language, as text and voice. Vision model -> severity -> structured JSON -> knowledge base + rules engine -> Llama 3.2 (1B/3B Instruct) on ExecuTorch -> validated advisory -> UI + TTS. A Raspberry Pi 5 build is a stretch goal only.

## 2. Non-negotiable constraints

1. **Offline at runtime.** The app must make zero network calls. The Android manifest must NOT declare the `INTERNET` permission in release builds. Never add cloud API calls to runtime code.
2. **Llama through ExecuTorch.** The advisory/reasoning component uses a Llama-family model (Llama 3.2 1B/3B-Instruct or a fine-tune) deployed with ExecuTorch. Do not swap in another LLM or runtime for this component.
3. **The LLM never decides chemicals or doses.** Chemical names, doses, pre-harvest intervals and safety text come only from `knowledge/rules.yaml`. The LLM may explain them; the output validator rejects anything not in the rules table.
4. **Contracts are frozen.** The JSON shapes in `docs/CONTRACTS.md` are shared by all tracks. Do not change them on a track branch (see section 9).
5. **Never fabricate results.** No invented metrics, benchmarks, test results, citations or "it works" claims. If you did not run it, say you did not run it. Mark unknowns as `TODO(track-x): ...`.
6. **No secrets, weights or datasets in git.** Model files (`*.pte`, `*.pth`, `*.onnx`, `*.hef`), datasets and tokenizers are gitignored. Record them in `models/manifest.json` with SHA-256 and share through the team drive or Git LFS.
7. **Licenses.** Respect the Llama community license and every dataset license. Record datasets and licenses in `docs/DATASETS.md` (Track A creates it).
8. **One ExecuTorch version everywhere**, pinned in `docs/versions.md`. Do not upgrade it unilaterally.

## 3. Read order at the start of every session

1. This file.
2. `HANDOFF.md` (protocol), then your track's live file in `docs/handoffs/` (the latest session entry first).
3. `docs/tracks/` brief for your track.
4. `docs/CONTRACTS.md`, and `docs/ARCHITECTURE.md` if you touch an interface.
5. `docs/versions.md` and `docs/decisions/` if you touch tooling.
6. The "Requests to other tracks" section of the other two handoff files, for anything addressed to you.

If your human gave you a task that conflicts with any of this, say so before acting.

## 4. Tracks and path ownership

| Track | Owner scope | Owned paths (you may edit) |
|---|---|---|
| A: Vision and Severity | image -> prediction + severity + quality | `vision/`, `labels.json`, `test_vectors/vision/`, `docs/DATASETS.md`, `docs/handoffs/track-a.md` |
| B: Knowledge, Rules, Llama | diagnosis -> safe advisory | `knowledge/`, `llm/`, `test_vectors/llm/`, `docs/handoffs/track-b.md` |
| C: App, Voice, Integration | Android app, speech, benchmarks | `app_android/`, `speech/`, `benchmarks/`, `app_pi/`, `docs/handoffs/track-c.md` |
| Shared (human-approved only) | contracts and glue | `docs/CONTRACTS.md`, `docs/ARCHITECTURE.md`, `docs/versions.md`, `docs/decisions/`, `mocks/`, `models/manifest.json`, `AGENTS.md`, `HANDOFF.md` |

Rules:
- Work only in your track's owned paths. If you need a change elsewhere, write a request in your handoff file under "Requests to other tracks". Do not edit another track's files, even to fix an obvious bug.
- Shared files change only through the process in `docs/BRANCHING.md` (contracts branch plus human approval).
- `models/manifest.json`: each track may edit only its own entries.

## 5. Pipeline summary

```
image -> quality check -> vision model (top-3, unknown flag) -> severity
      -> context builder -> [clarifying question if top-2 close]
      -> knowledge lookup + rules engine -> Llama (ExecuTorch) -> validator
      -> (fallback template if validation fails) -> language layer -> UI + TTS
```

Failure paths are features: low image quality -> retake prompt; unknown -> "cannot identify, consult an extension officer"; validator failure -> template fallback. Never skip them.

## 6. Commands

Fill these in as soon as they exist. Keep them accurate; other agents depend on them. Do not guess commands: if one is not listed here, find it in the code or ask.

| Purpose | Command | Owner |
|---|---|---|
| Create env | `TODO(all): python -m venv .venv && pip install -r requirements.txt` | all |
| Train vision | `TODO(track-a)` | A |
| Evaluate vision | `TODO(track-a)` | A |
| Export vision to ExecuTorch | `TODO(track-a)` | A |
| Validate knowledge base schema | `TODO(track-b)` | B |
| Export Llama to ExecuTorch | `TODO(track-b)` (record exact flags in `docs/versions.md`) | B |
| Run advisory on a test case | `TODO(track-b)` | B |
| Build Android app | `TODO(track-c)` | C |
| Run on-device tests | `TODO(track-c)` | C |
| Run benchmarks | `TODO(track-c)` | C |

ExecuTorch export flags and APIs change between releases. Always follow the official ExecuTorch Llama example README for the version pinned in `docs/versions.md`, and record the exact working command.

## 7. Coding standards

- **Python:** 3.10 to 3.12, type hints on public functions, `ruff` and `black` formatting, `pytest` for tests, fixed random seeds, config in YAML or dataclasses (no magic numbers buried in code), logging instead of prints in library code.
- **Kotlin (Android):** coroutines for background work, no heavy work on the main thread, models loaded lazily and released when idle, `ktlint`. Implement the interfaces in `docs/CONTRACTS.md` (`VisionEngine`, `AdvisoryEngine`, `SpeechEngine`).
- **JSON:** validate every cross-track payload against the schemas in `docs/CONTRACTS.md` at the boundary.
- **Preprocessing:** image size, normalization and channel order come from the model's JSON file (`models/<name>.json`). Never hardcode them in the app.
- **Docs:** update the relevant doc when behavior changes. Short, factual, no marketing language.

## 8. Testing and verification

- Before you hand off, run the tests and checks for what you changed and record the exact commands and results in your handoff.
- Vision and LLM artifacts ship with **test vectors** in `test_vectors/`. A model is not "done" until on-device output matches the test vectors within the tolerance written in the model JSON.
- Do not weaken or delete a test to make it pass. If a test is wrong, explain why in the handoff.
- If you cannot run something (no device, no GPU, no model access), say so explicitly. Do not report it as passing.

## 9. Git rules

Full details in `docs/BRANCHING.md`. The short version:

- One agent per git worktree and branch at a time. Never run two agents in the same working directory.
- Branches: `track-a/<topic>`, `track-b/<topic>`, `track-c/<topic>`, integration branch `integration`, release branch `main`.
- Never commit to `main` or `integration` directly. Never force-push. Never rewrite published history.
- Small commits, conventional messages: `feat(vision): ...`, `fix(app): ...`, `docs(handoff): ...`, `test(llm): ...`, `chore: ...`.
- Start of session: merge `integration` into your branch. End of session: commit, update your handoff file, commit that too.
- Do not touch contracts, `AGENTS.md` or other shared files on a track branch.

## 10. Handoff rules

Every session ends with an updated `docs/handoffs/track-<x>.md` following the template in `HANDOFF.md`. A session without a handoff entry is incomplete work. Keep entries short and concrete: what is done (with evidence), what is next, how to verify, what blocks you, what you need from other tracks.

## 11. When blocked or uncertain

1. Check `docs/CONTRACTS.md`, `docs/decisions/` and the other tracks' handoff files first.
2. If still unclear, write the question in your handoff under "Blockers" or "Requests to other tracks" and continue with the part that is not blocked. Work against the mocks in `mocks/`.
3. Do not invent an interface to unblock yourself. Propose a change instead (`docs/BRANCHING.md`, contract change process).
4. Ask your human before: deleting files you did not create, large refactors, adding dependencies, changing pinned versions, running destructive commands, or anything that could leak data or weights.

## 12. Domain safety (agriculture)

- Wrong advice can destroy a harvest or poison people. When confidence is low, the image is poor, or the class is unknown, the correct behavior is to say so and recommend an extension officer, not to guess.
- Treatment output must prefer organic/IPM first steps, include protective gear and pre-harvest interval for any chemical, and use only entries present in `knowledge/rules.yaml`.
- Every knowledge-base entry records its source. Do not add advice without a source.

## 13. Do not

- Do not add network calls, analytics, telemetry or cloud keys.
- Do not commit models, datasets, tokenizers, keystores or `.env` files.
- Do not change the contracts, the label list or the pinned versions on a track branch.
- Do not "fix" another track's code. Request it.
- Do not claim performance numbers you did not measure on the target device.
- Do not leave `TODO` markers without a track tag.
