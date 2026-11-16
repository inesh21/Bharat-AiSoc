# Track C: App, Voice and Integration (agent brief)

**Mission:** a smooth offline Android app that hosts both models, speaks and listens in local languages, and holds the whole system together. Track C also owns benchmarks, the demo video and the final report compilation.

**Owned paths:** `app_android/`, `speech/`, `benchmarks/`, `app_pi/` (stretch), `docs/handoffs/track-c.md`.

**Produces:** the APK, the benchmark results, the integration test report, the demo video, the compiled technical report.
**Consumes:** Track A's vision artifacts and Track B's Llama artifacts plus their test vectors; Contracts 1 to 3.

## Tasks

- [ ] **C1** Day 1: Android Studio, SDK, the NDK version required by the ExecuTorch Android README, USB debugging, `adb devices` shows the phone.
- [ ] **C2** Build the ExecuTorch Android library and run the reference Llama demo app with a pre-exported Llama 3.2 1B `.pte`. Record time to first token, tokens per second, RAM and crashes. This is the baseline.
- [ ] **C3** App module boundaries: `VisionEngine`, `AdvisoryEngine`, `SpeechEngine`, `Repository` (interfaces in `docs/CONTRACTS.md`).
- [ ] **C4** Build the UI against **mock** engines first (payloads from `mocks/`), so the UI is never blocked.
- [ ] **C5** Screens: language picker -> camera with framing guide and quality hints -> result card (label, confidence, severity with color and icon) -> advisory (text and audio) -> clarifying questions (buttons and voice) -> history.
- [ ] **C6** CameraX capture and preprocessing identical to Track A's, read from the sidecar JSON. Mismatched preprocessing is the most common integration bug.
- [ ] **C7** Integrate the vision `.pte` through ExecuTorch; verify against Track A's test vectors on the phone (milestone I2).
- [ ] **C8** Integrate the Llama `.pte`; run generation on a background thread and stream tokens to the UI; unload the vision model during generation if memory is tight (milestone I3).
- [ ] **C9** Speech: offline STT (Whisper tiny/base via whisper.cpp, Vosk, or an Indic model) and offline TTS (Android offline voices, Piper, or an Indic TTS model). Verify early that a voice exists for each chosen language.
- [ ] **C10** Storage: Room/SQLite for scan history and (stretch) a sync queue.
- [ ] **C11** Offline proof: no `INTERNET` permission in the release manifest; airplane-mode test and screen recording.
- [ ] **C12** Benchmark harness: 10-run loops recording vision latency, LLM time to first token, tokens per second, total scan time, peak RAM, battery and temperature into `benchmarks/results.csv`.
- [ ] **C13** Demo video, signed APK, integration test report, compiled technical report.

## Definition of done

- A full scan works in airplane mode on the target phone within the agreed end-to-end time, with no crashes over 50 consecutive scans.
- All failure paths in `docs/ARCHITECTURE.md` section 5 have UI.
- Benchmarks reflect real measurements on the target device.

## Integration points

- **From Track A and B:** artifacts per `HANDOFF.md` section 7. First action on receiving anything: run their test vectors.
- **To Track A and B:** device constraints (RAM budget, latency budget), measured numbers, and bug reports with reproduction steps and the failing test vector.

## Stretch (only after I4)

Raspberry Pi 5 build (vision via HailoRT on the Hailo NPU, Llama via ExecuTorch on the Arm CPU, documented as separate pipelines); store-and-forward outbreak sharing; extension-worker batch mode.

## Watch-outs

- Use the sidecar JSON for preprocessing; never hardcode.
- Never run model inference on the main thread.
- Test on a real mid-range phone before locking 1B vs 3B; laptop speed does not predict phone speed.
