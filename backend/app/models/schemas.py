from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.models.db_models import ChangeType, RequestStatus, ForgeryResult, AIRecommendation, CheckerDecisionValue


# ── Change Request ─────────────────────────────────────────────────────────────

class ChangeRequestCreate(BaseModel):
    customer_id: str = Field(..., example="C001")
    change_type: ChangeType = Field(..., example="LEGAL_NAME")
    requested_old_value: dict[str, Any] = Field(..., example={"name": "Priya Sharma"})
    requested_new_value: dict[str, Any] = Field(..., example={"name": "Priya Mehta"})


class ChangeRequestResponse(BaseModel):
    id: str
    customer_id: str
    change_type: str
    requested_old_value: dict[str, Any]
    requested_new_value: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Document ───────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    request_id: str
    document_type: str
    original_filename: str
    filenet_reference_id: Optional[str]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ── Verification Result ────────────────────────────────────────────────────────

class VerificationResultResponse(BaseModel):
    id: str
    request_id: str
    document_id: str
    extracted_fields: dict[str, Any]
    field_scores: dict[str, Any]
    overall_confidence: float
    forgery_check: str
    ai_summary: Optional[str]
    ai_recommendation: Optional[str]
    verified_at: datetime

    model_config = {"from_attributes": True}


# ── Checker ────────────────────────────────────────────────────────────────────

class CheckerDecisionCreate(BaseModel):
    checker_id: str = Field(..., example="CHECKER_001")
    decision: CheckerDecisionValue
    notes: Optional[str] = None


class CheckerDecisionResponse(BaseModel):
    id: str
    request_id: str
    checker_id: str
    decision: str
    notes: Optional[str]
    decided_at: datetime
    rps_response: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


# ── Full Review Detail (Checker UI) ───────────────────────────────────────────

class ReviewDetail(BaseModel):
    request: ChangeRequestResponse
    documents: list[DocumentResponse]
    verification: Optional[VerificationResultResponse]
    decisions: list[CheckerDecisionResponse]


# ── Pending List Item ──────────────────────────────────────────────────────────

class PendingRequestItem(BaseModel):
    id: str
    customer_id: str
    change_type: str
    requested_new_value: dict[str, Any]
    overall_confidence: Optional[float]
    ai_recommendation: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db_type: str
    llm_provider: str
    ocr_provider: str
