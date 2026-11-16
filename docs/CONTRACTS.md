# CONTRACTS.md: Interfaces shared by all tracks

These are frozen after milestone I0. Every cross-track payload is validated against these shapes at the boundary. To change anything here, use the contract change process in `docs/BRANCHING.md`. Current `schema_version`: **1.0**.

## 1. Shared artifacts

| Artifact | Owner | Rule |
|---|---|---|
| `labels.json` | Track A | The only list of class IDs. Format `crop__condition`, lowercase, underscores. Everyone uses these exact strings. Special classes: `unknown`, `<crop>__healthy`. |
| `models/manifest.json` | each track edits its own entries | One entry per model file (see 4). |
| `models/<name>.json` | model producer | Sidecar with preprocessing, labels or tokenizer info, thresholds, tolerance. |
| `mocks/` | shared | Sample payloads for every contract so no track waits on another. |
| `test_vectors/vision/`, `test_vectors/llm/` | A and B | Fixed inputs and expected outputs for on-device verification. |
| `docs/versions.md` | shared | Pinned tool versions, including ExecuTorch. |

## 2. Contract 1: Vision result (Track A -> B and C)

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

Field rules:
- `quality.issues` values: `blurry`, `too_dark`, `too_bright`, `no_leaf`.
- `type` values: `disease`, `pest`, `deficiency`, `healthy`.
- `predictions` are the top 3, sorted by confidence descending, confidences calibrated.
- `severity.band` values: `none`, `mild`, `moderate`, `severe`. `severity` may be `null` for pests or when not computable.
- If `quality.ok` is false or `unknown` is true: the app asks for a better photo or says it cannot identify. **Llama is not called.**

## 3. Contract 2: Advisory request (Track C -> B)

```json
{
  "schema_version": "1.0",
  "vision": { },
  "region": "region_code",
  "language": "en",
  "growth_stage": "unknown",
  "answers": [ { "question_id": "q_underside_spots", "answer": "yes" } ]
}
```

- `language`: ISO code, one of the languages in the project scope (`en`, `hi`, plus the chosen regional one).
- `growth_stage`: `seedling | vegetative | flowering | fruiting | unknown`.
- `answers[].answer`: `yes | no | not_sure`.

## 4. Contract 3: Advisory response (Track B -> C)

```json
{
  "schema_version": "1.0",
  "status": "final",
  "clarification": null,
  "diagnosis": "...",
  "severity_band": "moderate",
  "actions_now": ["..."],
  "prevention": ["..."],
  "seek_help": false,
  "source_ids": ["kb:tomato__early_blight"],
  "used_fallback": false,
  "language": "en",
  "text": "full text for display and TTS"
}
```

- `status`: `final` or `needs_clarification`.
- When `needs_clarification`: `clarification` is `{ "question_id": "...", "text": "...", "options": ["yes","no","not_sure"] }` and the other advice fields may be empty.
- `used_fallback` is `true` when the validator rejected the Llama output and the template fallback was used. The UI must work identically in both cases.
- Every chemical named must exist in `knowledge/rules.yaml`.

## 5. Kotlin interfaces (Track C implements; A and B supply what is behind them)

```kotlin
interface VisionEngine   { suspend fun analyze(bitmap: Bitmap): VisionResult }
interface AdvisoryEngine { fun advise(req: AdvisoryRequest, onToken: (String) -> Unit): AdvisoryResponse }
interface SpeechEngine   { fun listen(lang: String): String; fun speak(text: String, lang: String) }
```

## 6. Knowledge base entry (Track B)

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

Every `id` must exist in `labels.json`. Every entry must have at least one source.

## 7. Model sidecar JSON (`models/<name>.json`)

Vision example:
```json
{
  "name": "vision_v1",
  "task": "classification",
  "input": { "width": 224, "height": 224, "channels": "RGB", "layout": "NCHW", "dtype": "float32" },
  "normalization": { "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225] },
  "labels_file": "labels.json",
  "thresholds": { "unknown_score": 0.0, "min_confidence": 0.0 },
  "severity_bands": { "mild": [0, 10], "moderate": [10, 30], "severe": [30, 100] },
  "verification": { "test_vectors": "test_vectors/vision/", "max_abs_diff": 0.0 }
}
```
(Values above are placeholders. Track A fills in the real ones.)

LLM example fields: `name`, `base_model`, `quantization`, `max_seq_length`, `tokenizer_file`, `executorch_version`, `export_command`, `verification`.

## 8. Manifest entry (`models/manifest.json`)

```json
{
  "vision_v1": {
    "file": "vision_v1.pte",
    "sha256": "...",
    "size_bytes": 0,
    "date": "YYYY-MM-DD",
    "executorch_version": "see docs/versions.md",
    "producer": "track-a",
    "sidecar": "vision_v1.json"
  }
}
```

## 9. Compatibility rules

- Preprocessing used in the app must be identical to training/export preprocessing. The sidecar JSON is the only source of truth.
- A model exported with a different ExecuTorch version than the app runtime may fail to load. Never mix versions.
- Unknown extra JSON fields must be ignored by readers; missing required fields are a validation error.
- Bump `schema_version` for any change and update `mocks/`.
