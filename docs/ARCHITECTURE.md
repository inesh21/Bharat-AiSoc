# ARCHITECTURE.md

## 1. Pipeline

```
[Camera / Gallery]
      |
[Image quality check]  blur, brightness, leaf present?          (Track A)
      |
[Vision model]  crop, top-3 disease/pest, confidence, unknown   (Track A)
      |
[Severity]  lesion area % -> band                                (Track A)
      |
[Context builder]  vision JSON + region + language + stage       (Track B logic)
      |
[Clarifying question?]  only if top-2 are close                  (Track B logic, Track C UI)
      |
[Knowledge layer]  lookup by (crop, condition), retrieval,
                   rules engine (chemicals, doses, safety)       (Track B)
      |
[Llama 3.2 on ExecuTorch]  structured advisory                   (Track B model, Track C runtime)
      |
[Validator]  sections present, chemicals/doses match rules       (Track B)
      |   fail -> template fallback from the knowledge base
[Language layer]  Llama native or pre-translated slots           (Track B content, Track C UI strings)
      |
[UI + TTS]    [STT for follow-ups]    [Local DB history]         (Track C)
```

## 2. Three flows

| Flow | Owner | Input | Output |
|---|---|---|---|
| Perception | Track A | image | Contract 1 |
| Reasoning | Track B | Contract 2 | Contract 3 |
| Interaction | Track C | user actions, voice, camera | what the farmer sees, hears, says; hosts both models |

## 3. Runtime ownership

Track C owns running models inside the Android app (ExecuTorch Android library, threading, memory). Tracks A and B deliver packaged artifacts, sidecar JSON and test vectors, and prove them on a laptop first.

## 4. Memory and performance plan (phone)

- Vision model stays small. The Llama model is loaded on demand and unloaded when idle.
- If memory is tight, unload the vision model while Llama generates.
- Prompt length about 600 to 1200 tokens; `max_seq_length` set accordingly (KV cache grows with it).
- Choose 1B vs 3B from measured on-device numbers (time to first token, tokens/s, peak RAM, temperature), not from laptop speed.

## 5. Failure paths (must all be implemented in the UI)

| Condition | Behavior |
|---|---|
| `quality.ok == false` | Explain the issue (blurry, dark...) and ask to retake. No Llama call. |
| `unknown == true` | "Cannot identify. Please consult an extension officer." No Llama call. |
| Top-2 close | Ask 1 to 3 clarifying questions, re-weight, then advise. |
| Validator rejects Llama output | Use the template fallback (`used_fallback: true`). |
| Model fails to load / out of memory | Show a clear error; keep history usable; never crash. |

## 6. Hailo (Raspberry Pi stretch only)

If a Hailo accelerator is used for vision, vision runs through HailoRT on the Hailo NPU and Llama runs through ExecuTorch on the Pi Arm CPU. These are separate pipelines and must be documented as two separate boxes in the report.

## 7. Offline guarantee

No runtime network calls. Release manifest has no `INTERNET` permission. Demonstrate in airplane mode.
