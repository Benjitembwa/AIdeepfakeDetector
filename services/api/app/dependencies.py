from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models import MediaOrganization
from app.db.session import get_session

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")
SessionDep = Annotated[AsyncSession, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_media(session: SessionDep, token: TokenDep) -> MediaOrganization:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise ou jeton invalide.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        media_id = decode_access_token(token)
    except ValueError as exc:
        raise unauthorized from exc

    media = await session.get(MediaOrganization, media_id)
    if media is None or not media.is_active:
        raise unauthorized
    return media


CurrentMediaDep = Annotated[MediaOrganization, Depends(get_current_media)]
