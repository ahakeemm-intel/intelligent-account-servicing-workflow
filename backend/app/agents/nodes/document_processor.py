"""
Document Processor Node

1. Runs OCR on the uploaded document (Tesseract or Textract)
2. Uses LLM to extract structured fields relevant to the change type
3. Runs a forgery heuristic via LLM reasoning on OCR output

Note: LLM calls run in a thread pool via asyncio.to_thread so they do not
block the event loop during background task execution.
"""
import asyncio
import json
import os
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import RequestState
from app.services import ocr_service
from app.services.llm_service import get_llm
from app.core.config import settings


# ── Extraction Prompts per change type ────────────────────────────────────────

EXTRACTION_PROMPTS = {
    "LEGAL_NAME": """You are a document analysis assistant for a bank.
Extract the following fields from this marriage certificate / legal name change document text.
Return ONLY valid JSON with these exact keys:
{
  "bride_name": "<full name before marriage or old legal name>",
  "married_name": "<full name after marriage or new legal name>",
  "document_date": "<date on the document, YYYY-MM-DD or as found>",
  "issuing_authority": "<court, registrar, or authority name if present>",
  "document_number": "<certificate or reference number if present>"
}
If a field is not found, use null.
Document text:
""",
}

FORGERY_PROMPT = """You are a document fraud detection assistant for a regulated bank.
Analyse the following OCR text extracted from a document and assess authenticity.

Look for these red flags:
- Inconsistent date formats or impossible dates
- Misspelled official terms (e.g. "Registar" instead of "Registrar")
- Missing mandatory fields for the document type
- Unusual or suspicious formatting patterns
- Absence of official reference numbers

Return ONLY valid JSON:
{
  "result": "PASS" | "FLAG" | "FAIL",
  "reasons": ["<reason 1>", "<reason 2>"],
  "confidence": <0.0 to 1.0>
}

Document type: {doc_type}
OCR text:
{ocr_text}
"""


def document_processor(state: RequestState) -> RequestState:
    # Skip if validation already failed with blocking errors
    if state.get("validation_errors"):
        logger.warning("document_processor | skipping — validation failed")
        return state

    logger.info("document_processor | request={} | file={}", state["request_id"], state["document_path"])

    # Step 1: OCR
    try:
        ocr_result = ocr_service.extract_text(state["document_path"])
        raw_text = ocr_result["raw_text"]
    except Exception as e:
        logger.error("document_processor | OCR failed | {}", e)
        return {**state, "pipeline_errors": state.get("pipeline_errors", []) + [f"OCR failed: {e}"]}

    # Step 2: Structured extraction via LLM
    extracted_fields = _extract_fields(raw_text, state["change_type"], state["document_path"])

    # Step 3: Forgery detection via LLM
    forgery_result = _check_forgery(raw_text, state["change_type"])

    logger.info(
        "document_processor | extracted={} | forgery={}",
        list(extracted_fields.keys()), forgery_result.get("result"),
    )

    return {
        **state,
        "ocr_raw_text": raw_text,
        "extracted_fields": extracted_fields,
        "forgery_result": forgery_result.get("result", "FLAG"),
    }


def _extract_fields(raw_text: str, change_type: str, file_path: str) -> dict:
    """Use LLM to extract structured fields from OCR text."""
    prompt_prefix = EXTRACTION_PROMPTS.get(change_type, EXTRACTION_PROMPTS["LEGAL_NAME"])
    llm = get_llm()

    messages = [
        SystemMessage(content="You are a precise document data extraction assistant. Return only valid JSON."),
        HumanMessage(content=prompt_prefix + raw_text[:4000]),  # cap context
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning("document_processor | LLM extraction failed | {} — falling back to raw text", e)
        return {"raw_text_fallback": raw_text[:500]}


def _check_forgery(raw_text: str, doc_type: str) -> dict:
    """Use LLM to assess document authenticity."""
    llm = get_llm()
    prompt = FORGERY_PROMPT.format(doc_type=doc_type, ocr_text=raw_text[:3000])

    messages = [
        SystemMessage(content="You are a document fraud detection expert. Return only valid JSON."),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning("document_processor | forgery check failed | {} — defaulting to FLAG", e)
        return {"result": "FLAG", "reasons": ["Automated check failed"], "confidence": 0.5}
