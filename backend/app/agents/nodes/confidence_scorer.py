"""
Confidence Scorer Node

Computes per-field confidence scores by combining:
  1. Fuzzy string similarity (rapidfuzz) for name/text fields
  2. LLM semantic scoring for ambiguous matches

Thresholds (configurable via env):
  PASS  ≥ CONFIDENCE_PASS_THRESHOLD (default 0.90)
  FLAG  ≥ CONFIDENCE_FLAG_THRESHOLD (default 0.60)
  FAIL  <  CONFIDENCE_FLAG_THRESHOLD
"""
import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import RequestState
from app.services.llm_service import get_llm
from app.core.config import settings


def confidence_scorer(state: RequestState) -> RequestState:
    if state.get("pipeline_errors"):
        logger.warning("confidence_scorer | skipping — pipeline has errors")
        return state

    logger.info("confidence_scorer | request={}", state["request_id"])

    extracted = state.get("extracted_fields", {})
    old_value = state.get("old_value", {})
    new_value = state.get("new_value", {})
    change_type = state["change_type"]

    field_scores: dict[str, float] = {}

    if change_type == "LEGAL_NAME":
        # Score 1: Old name (bride_name) match
        extracted_old = extracted.get("bride_name") or ""
        requested_old = old_value.get("name", "")
        field_scores["old_name_match"] = _fuzzy_score(extracted_old, requested_old)

        # Score 2: New name (married_name) match
        extracted_new = extracted.get("married_name") or ""
        requested_new = new_value.get("name", "")
        field_scores["new_name_match"] = _fuzzy_score(extracted_new, requested_new)

        # Score 3: Document authenticity (from forgery result)
        forgery = state.get("forgery_result", "FLAG")
        field_scores["document_authenticity"] = _forgery_to_score(forgery)

        # Score 4: LLM semantic cross-check (catches OCR errors / nick-names)
        if field_scores["new_name_match"] < settings.CONFIDENCE_PASS_THRESHOLD:
            llm_score = _llm_semantic_score(extracted_new, requested_new)
            field_scores["new_name_match"] = max(field_scores["new_name_match"], llm_score)

    else:
        # Generic scorer for other change types
        for key, val in extracted.items():
            if val and isinstance(val, str):
                requested_val = str(list(new_value.values())[0]) if new_value else ""
                field_scores[key] = _fuzzy_score(val, requested_val)

    # Overall confidence: weighted average
    if field_scores:
        weights = _get_weights(change_type, field_scores)
        overall = sum(field_scores[k] * weights.get(k, 1.0) for k in field_scores)
        overall /= sum(weights.get(k, 1.0) for k in field_scores)
    else:
        overall = 0.0

    logger.info(
        "confidence_scorer | scores={} | overall={:.2f}",
        {k: f"{v:.2f}" for k, v in field_scores.items()}, overall,
    )

    return {**state, "field_scores": field_scores, "overall_confidence": round(overall, 4)}


def _fuzzy_score(a: str, b: str) -> float:
    """Return normalised similarity score [0, 1] using rapidfuzz."""
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz
        return fuzz.token_sort_ratio(a.lower().strip(), b.lower().strip()) / 100.0
    except ImportError:
        # Fallback: simple character overlap ratio
        a, b = a.lower().strip(), b.lower().strip()
        if a == b:
            return 1.0
        common = sum(1 for c in a if c in b)
        return common / max(len(a), len(b))


def _llm_semantic_score(extracted: str, requested: str) -> float:
    """Ask LLM to judge semantic similarity for ambiguous matches."""
    llm = get_llm()
    prompt = f"""Are these two names referring to the same person?
Name A (from document): "{extracted}"
Name B (requested change): "{requested}"

Consider: nicknames, OCR errors, middle name differences, hyphenation.
Return ONLY valid JSON: {{"match": true|false, "confidence": <0.0-1.0>, "reasoning": "<brief>"}}"""

    try:
        response = llm.invoke([
            SystemMessage(content="You are a name matching expert. Return only JSON."),
            HumanMessage(content=prompt),
        ])
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        data = json.loads(content)
        score = float(data.get("confidence", 0.5))
        if not data.get("match", True):
            score = min(score, settings.CONFIDENCE_FLAG_THRESHOLD)
        logger.debug("LLM semantic score | extracted='{}' | requested='{}' | score={}", extracted, requested, score)
        return score
    except Exception as e:
        logger.warning("LLM semantic scoring failed | {} — using 0.5", e)
        return 0.5


def _forgery_to_score(result: str) -> float:
    """Convert forgery check result to a numeric confidence score."""
    return {"PASS": 1.0, "FLAG": 0.65, "FAIL": 0.1}.get(result, 0.5)


def _get_weights(change_type: str, field_scores: dict) -> dict[str, float]:
    """Return per-field weights for the weighted average."""
    if change_type == "LEGAL_NAME":
        return {
            "old_name_match": 0.35,
            "new_name_match": 0.45,
            "document_authenticity": 0.20,
        }
    return {k: 1.0 for k in field_scores}
