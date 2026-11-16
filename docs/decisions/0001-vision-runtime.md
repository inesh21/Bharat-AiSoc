# 0001: Vision runtime
Date: TODO
Status: proposed
Deciders: Track A, Track C humans (Track B informed)

## Context
Llama must run on ExecuTorch. The vision model could use the same runtime or another. One runtime is simpler to build, document and explain. Decision needed by Day 3 so Track A can plan the export and Track C can plan the app.

## Options considered
1. ExecuTorch (XNNPACK) for vision as well (one runtime story, one set of native libraries in the app).
2. ONNX Runtime or TFLite for vision only (possibly easier model conversion for some architectures).

## Decision
Prefer option 1. Fall back to option 2 only if the chosen vision architecture cannot be exported to ExecuTorch with acceptable accuracy by Day 3. Final choice: TODO

## Consequences
- Track A exports according to the final choice and records the command in `docs/versions.md`.
- Track C includes the matching runtime in the app and keeps `VisionEngine` behind the interface so the runtime can change without UI changes.
