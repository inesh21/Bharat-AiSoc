# Track B: Knowledge Base, Rules Engine, and Llama Advisory

This directory houses the offline reasoning and advisory engine for the Offline Crop Disease Assistant.

## Key Subsystems

1. **`knowledge/rules.yaml` (Safety Matrix)**:
   - Ground truth registry of approved chemicals, dosages, active ingredients, pre-harvest intervals (PHI), and safety gear requirements.
   - Non-negotiable constraint: The LLM explains chemicals; `rules.yaml` strictly decides them.

2. **`knowledge/kb.json` (Agronomy Knowledge Base)**:
   - Curated agricultural entries covering 19 conditions across 5 focus crops (`tomato`, `potato`, `rice`, `maize`, `cotton`), pest (`fall_armyworm`), and `unknown`.
   - Every entry includes symptoms, favoring conditions, severity-stratified actions, organic options, and public authority citations (ICAR, TNAU, IRRI, CIMMYT).

3. **`knowledge/clarifications.yaml` & `knowledge/clarifications.py` (Task B5)**:
   - Evaluates ambiguity when top 2 diagnoses have confidence difference < 0.15.
   - Returns a targeted, farmer-observable clarifying question and updates prediction weights based on the response.

4. **`llm/prompts.py` (Task B6, B7)**:
   - Structured context-efficient prompts (600 - 1200 tokens) strictly confining generation to provided reference facts.

5. **`llm/validator.py` (Task B8)**:
   - Validates LLM outputs for JSON schema compliance and intercepts hallucinated/unauthorized/banned chemicals.
   - Triggers deterministic knowledge-base fallback when invalid.

6. **`llm/pipeline.py` (Contract 2 & 3 Compliance)**:
   - Orchestrates Contract 2 (`AdvisoryRequest`) -> Clarification Loop -> KB Retrieval -> Model/Fallback -> Localization -> Contract 3 (`AdvisoryResponse`).

## Verification
```bash
python -m pytest llm/test_advisory.py -v
```
