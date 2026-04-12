import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from datetime import datetime
from app.api.deps import get_db
from app.models.db_models import ChangeRequest, VerificationResult, CheckerDecision, RequestStatus, CheckerDecisionValue
from app.models.schemas import (
    ReviewDetail, PendingRequestItem, CheckerDecisionCreate, CheckerDecisionResponse,
    ChangeRequestResponse, DocumentResponse, VerificationResultResponse,
)
from app.services import rps_service

router = APIRouter(prefix="/api/v1/checker", tags=["Checker"])


@router.get("/pending", response_model=list[PendingRequestItem])
async def list_pending_requests(db: AsyncSession = Depends(get_db)):
    """List all requests awaiting human Checker review."""
    result = await db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.status == RequestStatus.AI_VERIFIED_PENDING_HUMAN)
        .order_by(ChangeRequest.created_at.desc())
        .options(selectinload(ChangeRequest.verification_results))
    )
    requests = result.scalars().all()

    items = []
    for req in requests:
        vr = req.verification_results[-1] if req.verification_results else None
        items.append(PendingRequestItem(
            id=req.id,
            customer_id=req.customer_id,
            change_type=req.change_type,
            requested_new_value=req.requested_new_value,
            overall_confidence=vr.overall_confidence if vr else None,
            ai_recommendation=vr.ai_recommendation if vr else None,
            created_at=req.created_at,
        ))
    return items


@router.get("/requests/{request_id}", response_model=ReviewDetail)
async def get_review_detail(request_id: str, db: AsyncSession = Depends(get_db)):
    """Return full review detail for the Checker UI."""
    result = await db.execute(
        select(ChangeRequest)
        .where(ChangeRequest.id == request_id)
        .options(
            selectinload(ChangeRequest.documents),
            selectinload(ChangeRequest.verification_results),
            selectinload(ChangeRequest.checker_decisions),
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    vr = req.verification_results[-1] if req.verification_results else None

    return ReviewDetail(
        request=ChangeRequestResponse.model_validate(req),
        documents=[DocumentResponse.model_validate(d) for d in req.documents],
        verification=VerificationResultResponse.model_validate(vr) if vr else None,
        decisions=[CheckerDecisionResponse.model_validate(d) for d in req.checker_decisions],
    )


@router.post("/requests/{request_id}/approve", response_model=CheckerDecisionResponse)
async def approve_request(
    request_id: str,
    payload: CheckerDecisionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Checker approves the request.

    HITL enforcement: this is the ONLY function that calls the RPS write.
    The write is gated behind a human decision recorded in checker_decisions.
    """
    req = await db.get(ChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status not in (RequestStatus.AI_VERIFIED_PENDING_HUMAN,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is in status '{req.status}' — cannot approve",
        )

    # Create checker decision record FIRST, before RPS write
    decision = CheckerDecision(
        id=str(uuid.uuid4()),
        request_id=request_id,
        checker_id=payload.checker_id,
        decision=CheckerDecisionValue.APPROVED,
        notes=payload.notes,
        decided_at=datetime.utcnow(),
    )
    db.add(decision)
    await db.flush()

    # Trigger mock RPS write — requires the decision ID (HITL gate)
    try:
        rps_response = rps_service.write_customer_record(
            customer_id=req.customer_id,
            change_type=req.change_type,
            new_value=req.requested_new_value,
            checker_decision_id=decision.id,
        )
        decision.rps_response = rps_response
    except Exception as e:
        logger.error("RPS write failed | request={} | {}", request_id, e)
        raise HTTPException(status_code=500, detail=f"RPS write failed: {e}")

    req.status = RequestStatus.APPROVED
    req.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(decision)

    logger.info(
        "checker APPROVED | request={} | checker={} | decision={}",
        request_id, payload.checker_id, decision.id,
    )
    return decision


@router.post("/requests/{request_id}/reject", response_model=CheckerDecisionResponse)
async def reject_request(
    request_id: str,
    payload: CheckerDecisionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Checker rejects the request. No RPS write occurs."""
    req = await db.get(ChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status not in (RequestStatus.AI_VERIFIED_PENDING_HUMAN,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is in status '{req.status}' — cannot reject",
        )

    decision = CheckerDecision(
        id=str(uuid.uuid4()),
        request_id=request_id,
        checker_id=payload.checker_id,
        decision=CheckerDecisionValue.REJECTED,
        notes=payload.notes,
        decided_at=datetime.utcnow(),
        rps_response={"status": "NOT_EXECUTED", "reason": "Rejected by checker"},
    )
    db.add(decision)
    req.status = RequestStatus.REJECTED
    req.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(decision)

    logger.info(
        "checker REJECTED | request={} | checker={} | decision={}",
        request_id, payload.checker_id, decision.id,
    )
    return decision
