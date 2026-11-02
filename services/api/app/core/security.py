from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("prisme-dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise ValueError("Unexpected token type")
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid access token") from exc
