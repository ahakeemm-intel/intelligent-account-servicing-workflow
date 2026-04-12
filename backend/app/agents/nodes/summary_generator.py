"""
Summary Generator Node

Uses LLM to produce a human-readable review summary and a recommended action
for the human Checker. This is the final node in the pipeline — its output
is staged to the DB and displayed on the Checker Review UI.
"""
import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import RequestState
from app.services.llm_service import get_llm
from app.core.config import settings


SUMMARY_PROMPT = """You are an AI assistant helping a banking compliance checker review an account change request.

Generate a concise, professional review summary for the checker based on the data below.
Include: what was found in the document, how well it matches the request, and a clear recommended action.

Change Request:
- Customer ID: {customer_id}
- Change Type: {change_type}
- Old Value: {old_value}
- New Value: {new_value}

Document Extraction Results:
{extracted_fields}

Confidence Scores:
{field_scores}

Overall Confidence: {overall_confidence:.0%}
Forgery Check: {forgery_result}

Return ONLY valid JSON:
{{
  "summary": "<2-4 sentence professional summary for the checker>",
  "recommendation": "APPROVE" | "REJECT" | "FLAG_FOR_REVIEW",
  "recommendation_reason": "<one sentence explaining the recommendation>"
}}"""


def summary_generator(state: RequestState) -> RequestState:
    if state.get("pipeline_errors"):
        logger.warning("summary_generator | pipeline has errors — generating error summary")
        error_summary = "Document processing encountered errors: " + "; ".join(state["pipeline_errors"])
        return {
            **state,
            "ai_summary": error_summary,
            "ai_recommendation": "FLAG_FOR_REVIEW",
        }

    logger.info("summary_generator | request={}", state["request_id"])

    overall = state.get("overall_confidence", 0.0)
    field_scores = state.get("field_scores", {})
    extracted = state.get("extracted_fields", {})

    # Determine recommendation based on thresholds before calling LLM
    forgery = state.get("forgery_result", "FLAG")
    if forgery == "FAIL":
        fallback_rec = "REJECT"
    elif overall >= settings.CONFIDENCE_PASS_THRESHOLD and forgery == "PASS":
        fallback_rec = "APPROVE"
    elif overall >= settings.CONFIDENCE_FLAG_THRESHOLD:
        fallback_rec = "FLAG_FOR_REVIEW"
    else:
        fallback_rec = "REJECT"

    prompt = SUMMARY_PROMPT.format(
        customer_id=state["customer_id"],
        change_type=state["change_type"],
        old_value=json.dumps(state["old_value"]),
        new_value=json.dumps(state["new_value"]),
        extracted_fields=json.dumps(extracted, indent=2),
        field_scores=json.dumps({k: f"{v:.0%}" for k, v in field_scores.items()}, indent=2),
        overall_confidence=overall,
        forgery_result=forgery,
    )

    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content="You are a professional banking compliance assistant. Return only valid JSON."),
            HumanMessage(content=prompt),
        ])
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        data = json.loads(content)
        summary = data.get("summary", "")
        recommendation = data.get("recommendation", fallback_rec)
        logger.info("summary_generator | recommendation={} | confidence={:.2f}", recommendation, overall)
        return {**state, "ai_summary": summary, "ai_recommendation": recommendation}
    except Exception as e:
        logger.warning("summary_generator | LLM failed | {} — using rule-based fallback", e)
        summary = _rule_based_summary(state)
        return {**state, "ai_summary": summary, "ai_recommendation": fallback_rec}


def _rule_based_summary(state: RequestState) -> str:
    """Fallback summary when LLM call fails."""
    overall = state.get("overall_confidence", 0.0)
    forgery = state.get("forgery_result", "FLAG")
    old_name = state["old_value"].get("name", "")
    new_name = state["new_value"].get("name", "")
    return (
        f"Document processed for {state['change_type']} request. "
        f"Requested change: '{old_name}' → '{new_name}'. "
        f"Overall confidence: {overall:.0%}. "
        f"Forgery check: {forgery}. "
        f"Manual review recommended."
    )
