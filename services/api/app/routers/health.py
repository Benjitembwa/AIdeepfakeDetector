import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.dependencies import SessionDep
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["Santé"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.get("/ready", response_model=HealthResponse)
async def readiness(session: SessionDep) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("La vérification PostgreSQL a échoué")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de données n'est pas disponible.",
        ) from exc
    return HealthResponse(status="ok", service=settings.app_name, database="connected")
