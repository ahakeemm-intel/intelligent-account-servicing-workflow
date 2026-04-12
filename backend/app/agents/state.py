from typing import TypedDict, Optional, Any


class RequestState(TypedDict):
    # Input fields (set at job start)
    request_id: str
    customer_id: str
    change_type: str
    old_value: dict[str, Any]
    new_value: dict[str, Any]
    document_path: str
    document_id: str

    # Populated by validation_agent
    rps_record: Optional[dict[str, Any]]
    validation_errors: list[str]

    # Populated by document_processor
    ocr_raw_text: Optional[str]
    extracted_fields: Optional[dict[str, Any]]
    forgery_result: Optional[str]  # PASS | FLAG | FAIL

    # Populated by confidence_scorer
    field_scores: Optional[dict[str, float]]
    overall_confidence: Optional[float]

    # Populated by summary_generator
    ai_summary: Optional[str]
    ai_recommendation: Optional[str]  # APPROVE | REJECT | FLAG_FOR_REVIEW

    # Pipeline-level errors
    pipeline_errors: list[str]
