"""End-to-end Advisory Pipeline Engine for Track B (Contract 3 Compliant).

Orchestrates:
1. Clarification loop check (Task B5)
2. Knowledge retrieval from knowledge/kb.json (Task B4)
3. Safety rules enforcement from knowledge/rules.yaml (Task B3)
4. Prompt construction for Llama (Task B6)
5. Output validation with strict zero-chemical-hallucination guardrail (Task B8)
6. Fallback template generation on validator rejection (Task B8)
7. Multilingual localization (Task B9)
"""

from typing import Dict, Any, List, Optional, Callable
from knowledge.retrieval import KnowledgeBase
from knowledge.clarifications import ClarificationEngine
from llm.prompts import build_advisory_prompt, SYSTEM_PROMPT
from llm.validator import OutputValidator
from llm.language_layer import localize_advisory


class AdvisoryPipeline:
    """Full offline advisory pipeline converting Contract 2 requests to Contract 3 responses."""

    def __init__(
        self,
        kb_path: str = "knowledge/kb.json",
        rules_path: str = "knowledge/rules.yaml",
        clarifications_path: str = "knowledge/clarifications.yaml",
        llm_generate_fn: Optional[Callable[[str, str], str]] = None
    ):
        self.kb = KnowledgeBase(kb_path=kb_path, rules_path=rules_path)
        self.clarification_engine = ClarificationEngine(config_path=clarifications_path)
        self.validator = OutputValidator(rules_path=rules_path)
        self.llm_generate_fn = llm_generate_fn

    def advise(
        self,
        request: Dict[str, Any],
        on_token: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Processes Contract 2 AdvisoryRequest and emits Contract 3 AdvisoryResponse.

        Args:
            request: Contract 2 compliant request dictionary
            on_token: Optional callback for streaming tokens to UI/TTS

        Returns:
            Contract 3 compliant response dictionary
        """
        vision = request.get("vision", {})
        predictions = vision.get("predictions", [])
        lang = request.get("language", "en")
        answers = request.get("answers", [])
        severity = vision.get("severity", {}) or {}
        severity_band = severity.get("band", "moderate")

        # Handle early failure / unknown from vision
        if vision.get("unknown", False) or not vision.get("quality", {}).get("ok", True) or not predictions:
            return self.kb.build_fallback_advisory("unknown", severity_band="none", lang=lang)

        # 1. Clarification Check (Task B5)
        # Check if farmer has already answered a clarifying question
        if answers:
            ans = answers[0]
            # Apply answer to re-weight predictions
            ambiguity = self.clarification_engine.check_ambiguity(predictions, lang=lang)
            if ambiguity:
                predictions = self.clarification_engine.apply_answer(
                    pair_key=ambiguity.get("pair_key", ""),
                    question_id=ans.get("question_id", ""),
                    answer=ans.get("answer", ""),
                    predictions=predictions
                )
        else:
            ambiguity = self.clarification_engine.check_ambiguity(predictions, lang=lang)
            if ambiguity:
                # Return early with status="needs_clarification"
                return {
                    "schema_version": "1.0",
                    "status": "needs_clarification",
                    "clarification": {
                        "question_id": ambiguity["question_id"],
                        "text": ambiguity["text"],
                        "options": ambiguity["options"]
                    },
                    "diagnosis": f"Ambiguous between {predictions[0]['label']} and {predictions[1]['label']}",
                    "severity_band": severity_band,
                    "actions_now": [],
                    "prevention": [],
                    "seek_help": False,
                    "source_ids": [f"kb:{predictions[0]['label']}", f"kb:{predictions[1]['label']}"],
                    "used_fallback": False,
                    "language": lang,
                    "text": ambiguity["text"]
                }

        top_pred = predictions[0]
        condition_id = top_pred.get("label", "unknown")

        # 2. Knowledge Retrieval (Task B4)
        kb_entry = self.kb.get_entry(condition_id)
        if not kb_entry:
            return self.kb.build_fallback_advisory("unknown", severity_band="none", lang=lang)

        # 3. LLM Generation or Direct Fallback (Task B6, B8)
        used_fallback = False
        parsed_output = None

        if self.llm_generate_fn is not None:
            prompt = build_advisory_prompt(
                vision_result=vision,
                kb_entry=kb_entry,
                severity_band=severity_band,
                language=lang
            )
            raw_generation = self.llm_generate_fn(SYSTEM_PROMPT, prompt)

            # Output validation
            is_valid, parsed, rejection_reasons = self.validator.validate(
                llm_output_text=raw_generation,
                target_condition_id=condition_id,
                severity_band=severity_band
            )
            if is_valid and parsed:
                parsed_output = parsed
            else:
                # Fallback on validation rejection
                used_fallback = True
        else:
            used_fallback = True

        if used_fallback or parsed_output is None:
            response = self.kb.build_fallback_advisory(condition_id, severity_band=severity_band, lang=lang)
        else:
            # Construct verified Contract 3 response from valid LLM generation
            response = {
                "schema_version": "1.0",
                "status": "final",
                "clarification": None,
                "diagnosis": parsed_output.get("diagnosis", condition_id),
                "severity_band": severity_band,
                "actions_now": parsed_output.get("actions_now", []),
                "prevention": parsed_output.get("prevention", []),
                "seek_help": condition_id == "unknown",
                "source_ids": [f"kb:{condition_id}"],
                "used_fallback": False,
                "language": lang,
                "text": parsed_output.get("summary_text", "")
            }

        # Apply localization if necessary
        response = localize_advisory(response, lang=lang)

        # Stream tokens if callback provided
        if on_token and response.get("text"):
            for tok in response["text"].split(" "):
                on_token(f"{tok} ")

        return response
