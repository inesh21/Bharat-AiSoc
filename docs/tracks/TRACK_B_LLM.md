# Track B: Knowledge, Rules and Llama (agent brief)

**Mission:** turn a diagnosis into safe, correct, grounded, multilingual advice using Llama 3.2 on ExecuTorch, with guardrails so it can never give unsafe output.

**Owned paths:** `knowledge/`, `llm/`, `test_vectors/llm/`, `docs/handoffs/track-b.md`, your entries in `models/manifest.json`.

**Produces:** Contract 3 (advisory response), knowledge base, `rules.yaml`, prompts, validator, `models/llama32_1b_vX.pte` + tokenizer + `llama_config.json`, test vectors, evaluation set.
**Consumes:** Contract 1 samples and `labels.json` from Track A; the Contract 2 request shape from Track C.

## Tasks

- [ ] **B1** **Day 1 risk task.** Request Llama 3.2 access (Hugging Face and Meta). Export stock Llama 3.2 1B-Instruct to a quantized `.pte` with the ExecuTorch Llama example for the pinned version, run it on the laptop, and record the exact working command in `docs/versions.md` via a decision/contracts change. Share the file with Track C.
- [ ] **B2** Knowledge base: one JSON entry per class in `labels.json`, from trusted public extension sources, with source and date.
- [ ] **B3** `knowledge/rules.yaml`: chemical names, doses, pre-harvest interval, protective gear, restricted items for the region, "see extension officer" triggers. Every chemical line verified against a source or a domain expert.
- [ ] **B4** Retrieval: deterministic lookup by (crop, condition) first; BM25 or a small multilingual embedding model only for free-form follow-ups.
- [ ] **B5** Clarifying questions: for each commonly confused disease pair, 1 to 3 yes/no discriminating questions and how each answer re-weights the candidates (a small table, no model needed).
- [ ] **B6** Prompts: system prompt (role, "use only the provided context", required sections, short sentences, no invented chemicals or doses, say so when unsure) and a user template filled from vision JSON plus knowledge snippets.
- [ ] **B7** Context budget: prompts about 600 to 1200 tokens; set `max_seq_length` accordingly.
- [ ] **B8** Output validator: required sections present; chemicals exist in the rules table; doses match; otherwise return the template fallback built from the knowledge base.
- [ ] **B9** Language layer: Llama generates directly for languages it supports (for example English, Hindi). For other regional languages use pre-translated knowledge entries and slot templates reviewed by a native speaker, or a separate small offline translation model documented as its own component.
- [ ] **B10** Evaluation set of 100 to 200 cases (vision JSON -> expected advice facts) and a checklist: correct diagnosis, severity-appropriate advice, consistent with the knowledge base, no unsafe dose, language quality.
- [ ] **B11** Compare 1B vs 3B quality on the evaluation set. Track C measures latency on the phone.
- [ ] **B12** (Stretch) Synthetic Q&A data, LoRA fine-tune of 1B, ablation against the untuned model.

## Definition of done

- 100 percent of advisories pass the validator or use the fallback.
- Zero invented chemicals or doses in the evaluation set.
- Required sections present in more than 95 percent of outputs.
- Native-speaker review of at least 20 outputs per supported language.
- `.pte` runs on the phone and matches test vectors (milestone I3).

## Integration points

- **To Track C:** `.pte`, tokenizer, `llama_config.json`, manifest entry, 30 prompt test vectors, the prompt templates, and the advisory function signature matching Contract 2/3.
- **From Track A:** realistic Contract 1 samples; confusable class pairs that need clarifying questions.
- **From Track C:** measured TTFT, tokens/s and RAM to decide 1B vs 3B and the context length.

## Watch-outs

- Export flags change between ExecuTorch versions; follow the official README for the pinned version.
- Llama 3.2 officially supports a limited set of languages; do not assume it can write your regional language well. Measure it.
- The LLM explains; the rules table decides. Never let generated text introduce a product or dose.
