import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from app.core.database import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────────────

class ChangeType(str, enum.Enum):
    LEGAL_NAME = "LEGAL_NAME"
    ADDRESS = "ADDRESS"
    DOB = "DOB"
    CONTACT = "CONTACT"


class RequestStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    AI_VERIFIED_PENDING_HUMAN = "AI_VERIFIED_PENDING_HUMAN"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ForgeryResult(str, enum.Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    FAIL = "FAIL"


class AIRecommendation(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


class CheckerDecisionValue(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── Models ─────────────────────────────────────────────────────────────────────

class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_old_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    requested_new_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=RequestStatus.INITIATED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="change_request", cascade="all, delete-orphan")
    verification_results: Mapped[list["VerificationResult"]] = relationship("VerificationResult", back_populates="change_request", cascade="all, delete-orphan")
    checker_decisions: Mapped[list["CheckerDecision"]] = relationship("CheckerDecision", back_populates="change_request", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filenet_reference_id: Mapped[str] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    change_request: Mapped["ChangeRequest"] = relationship("ChangeRequest", back_populates="documents")
    verification_results: Mapped[list["VerificationResult"]] = relationship("VerificationResult", back_populates="document")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    extracted_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    field_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    forgery_check: Mapped[str] = mapped_column(String(10), nullable=False, default=ForgeryResult.FLAG)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)
    ai_recommendation: Mapped[str] = mapped_column(String(20), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    change_request: Mapped["ChangeRequest"] = relationship("ChangeRequest", back_populates="verification_results")
    document: Mapped["Document"] = relationship("Document", back_populates="verification_results")


class CheckerDecision(Base):
    __tablename__ = "checker_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("change_requests.id"), nullable=False)
    checker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    rps_response: Mapped[dict] = mapped_column(JSON, nullable=True)

    change_request: Mapped["ChangeRequest"] = relationship("ChangeRequest", back_populates="checker_decisions")
