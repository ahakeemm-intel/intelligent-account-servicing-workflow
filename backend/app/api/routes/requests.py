import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from app.api.deps import get_db
from app.models.db_models import ChangeRequest, RequestStatus
from app.models.schemas import ChangeRequestCreate, ChangeRequestResponse
from app.services import rps_service

router = APIRouter(prefix="/api/v1/requests", tags=["Change Requests"])


@router.post("", response_model=ChangeRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_change_request(
    payload: ChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new change request. Validates customer exists in RPS."""
    customer = rps_service.get_customer(payload.customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{payload.customer_id}' not found in RPS",
        )

    req = ChangeRequest(
        id=str(uuid.uuid4()),
        customer_id=payload.customer_id,
        change_type=payload.change_type,
        requested_old_value=payload.requested_old_value,
        requested_new_value=payload.requested_new_value,
        status=RequestStatus.INITIATED,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    logger.info("change_request created | id={} | customer={} | type={}", req.id, req.customer_id, req.change_type)
    return req


@router.get("/{request_id}", response_model=ChangeRequestResponse)
async def get_change_request(request_id: str, db: AsyncSession = Depends(get_db)):
    req = await db.get(ChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req
