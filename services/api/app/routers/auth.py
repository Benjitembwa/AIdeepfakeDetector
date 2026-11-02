import re
import unicodedata
from uuid import uuid4

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models import MediaOrganization
from app.dependencies import SessionDep
from app.schemas import MediaPublic, MediaRegister, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentification"])


def make_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:140] or "media"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: MediaRegister, session: SessionDep) -> TokenResponse:
    email = str(payload.email).lower()
    duplicate = await session.scalar(
        select(MediaOrganization.id).where(
            or_(
                func.lower(MediaOrganization.email) == email,
                func.lower(MediaOrganization.name) == payload.organization_name.lower(),
            )
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte utilise déjà cette adresse ou ce nom de média.",
        )

    base_slug = make_slug(payload.organization_name)
    slug = base_slug
    if await session.scalar(select(MediaOrganization.id).where(MediaOrganization.slug == slug)):
        slug = f"{base_slug}-{uuid4().hex[:6]}"

    media = MediaOrganization(
        name=payload.organization_name,
        slug=slug,
        email=email,
        password_hash=hash_password(payload.password),
    )
    session.add(media)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce compte média existe déjà.",
        ) from exc
    await session.refresh(media)
    token, expires_in = create_access_token(media.id)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        media=MediaPublic.model_validate(media),
    )


@router.post("/token", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> TokenResponse:
    email = form.username.strip().lower()
    media = await session.scalar(
        select(MediaOrganization).where(func.lower(MediaOrganization.email) == email)
    )
    password_matches = verify_password(
        form.password, media.password_hash if media is not None else DUMMY_HASH
    )
    if media is None or not password_matches or not media.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse e-mail ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(media.id)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        media=MediaPublic.model_validate(media),
    )
