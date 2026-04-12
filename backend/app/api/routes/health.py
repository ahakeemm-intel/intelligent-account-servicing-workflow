from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="ok",
        db_type=settings.DB_TYPE,
        llm_provider=settings.LLM_PROVIDER,
        ocr_provider=settings.OCR_PROVIDER,
    )
