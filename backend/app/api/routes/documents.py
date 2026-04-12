import uuid
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.api.deps import get_db
from app.models.db_models import ChangeRequest, Document, VerificationResult, RequestStatus
from app.models.schemas import DocumentResponse
from app.services import filenet_service
from app.agents.state import RequestState
from datetime import datetime

router = APIRouter(prefix="/api/v1/requests", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/{request_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request_id: str,
    background_tasks: BackgroundTasks,
    document_type: str = Form(..., examples=["marriage_certificate"]),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a supporting document for a change request.
    Archives to FileNet mock, then triggers the AI agent pipeline as a background task.
    Returns immediately with 202 — poll GET /requests/{id} for status updates.
    """
    req = await db.get(ChangeRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Permitted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content (enforce size limit)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    # Save to a temp file so services can open it by path
    suffix = ext
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Archive to FileNet mock
        stored_path, filenet_ref = filenet_service.archive_document(
            source_path=tmp_path,
            request_id=request_id,
            document_type=document_type,
            original_filename=file.filename or f"upload{ext}",
        )
    finally:
        os.unlink(tmp_path)

    # Persist document record
    doc = Document(
        id=str(uuid.uuid4()),
        request_id=request_id,
        document_type=document_type,
        file_path=stored_path,
        original_filename=file.filename or f"upload{ext}",
        filenet_reference_id=filenet_ref,
    )
    db.add(doc)

    # Mark request as PROCESSING and **commit immediately** before returning,
    # so the background task's separate session doesn't hit a SQLite write lock.
    req.status = RequestStatus.PROCESSING
    req.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(doc)

    # Trigger pipeline in background (non-blocking)
    background_tasks.add_task(
        _run_agent_pipeline,
        request_id=request_id,
        document_id=doc.id,
        document_path=stored_path,
        change_type=req.change_type,
        customer_id=req.customer_id,
        old_value=req.requested_old_value,
        new_value=req.requested_new_value,
    )
    logger.info("document uploaded | request={} | doc={} | ref={}", request_id, doc.id, filenet_ref)
    return doc


async def _run_agent_pipeline(
    request_id: str,
    document_id: str,
    document_path: str,
    change_type: str,
    customer_id: str,
    old_value: dict,
    new_value: dict,
):
    """Background task: runs the LangGraph pipeline and persists results."""
    import asyncio
    # Import here to avoid circular imports at module load time
    from app.core.database import AsyncSessionLocal

    initial_state: RequestState = {
        "request_id": request_id,
        "customer_id": customer_id,
        "change_type": change_type,
        "old_value": old_value,
        "new_value": new_value,
        "document_path": document_path,
        "document_id": document_id,
        "rps_record": None,
        "validation_errors": [],
        "ocr_raw_text": None,
        "extracted_fields": None,
        "forgery_result": None,
        "field_scores": None,
        "overall_confidence": None,
        "ai_summary": None,
        "ai_recommendation": None,
        "pipeline_errors": [],
    }

    try:
        # Run the pipeline in a thread pool — the synchronous LLM calls
        # (pytesseract, langchain llm.invoke) must not block the event loop.
        final_state = await asyncio.to_thread(_run_pipeline_sync, initial_state)
    except Exception as e:
        logger.error("pipeline crashed | request={} | {}", request_id, e)
        final_state = {**initial_state, "pipeline_errors": [str(e)], "ai_recommendation": "FLAG_FOR_REVIEW"}

    # Persist results to DB
    async with AsyncSessionLocal() as db:
        try:
            req = await db.get(ChangeRequest, request_id)
            if not req:
                return

            vr = VerificationResult(
                id=str(uuid.uuid4()),
                request_id=request_id,
                document_id=document_id,
                extracted_fields=final_state.get("extracted_fields") or {},
                field_scores=final_state.get("field_scores") or {},
                overall_confidence=final_state.get("overall_confidence") or 0.0,
                forgery_check=final_state.get("forgery_result") or "FLAG",
                ai_summary=final_state.get("ai_summary"),
                ai_recommendation=final_state.get("ai_recommendation"),
                verified_at=datetime.utcnow(),
            )
            db.add(vr)

            req.status = RequestStatus.AI_VERIFIED_PENDING_HUMAN
            req.updated_at = datetime.utcnow()
            await db.commit()
            logger.info("pipeline results persisted | request={} | status=AI_VERIFIED_PENDING_HUMAN", request_id)
        except Exception as e:
            await db.rollback()
            logger.error("failed to persist pipeline results | request={} | {}", request_id, e)


def _run_pipeline_sync(initial_state: RequestState) -> RequestState:
    """Run the async LangGraph pipeline synchronously in a thread."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        from app.agents.graph import run_pipeline
        return loop.run_until_complete(run_pipeline(initial_state))
    finally:
        loop.close()
