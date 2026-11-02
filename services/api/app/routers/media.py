from fastapi import APIRouter

from app.db.models import MediaOrganization
from app.dependencies import CurrentMediaDep
from app.schemas import MediaPublic

router = APIRouter(prefix="/media", tags=["Médias"])


@router.get("/me", response_model=MediaPublic)
async def read_current_media(media: CurrentMediaDep) -> MediaOrganization:
    return media
