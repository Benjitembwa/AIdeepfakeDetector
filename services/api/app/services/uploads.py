import io
import warnings
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PIXELS = 50_000_000


@dataclass(frozen=True)
class ValidatedUpload:
    contents: bytes
    width: int
    height: int
    media_type: str


def inspect_image(contents: bytes) -> tuple[int, int]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as candidate:
                candidate.verify()
            with Image.open(io.BytesIO(contents)) as candidate:
                width, height = candidate.size
                candidate.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Warning) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier ne contient pas une image valide ou sûre.",
        ) from exc
    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les dimensions de l'image ne sont pas acceptées.",
        )
    return width, height


async def validate_upload(image: UploadFile) -> ValidatedUpload:
    media_type = image.content_type or ""
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format non accepté. Utilisez JPG, PNG ou WebP.",
        )
    max_bytes = get_settings().max_upload_bytes
    contents = await image.read(max_bytes + 1)
    await image.close()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier image est vide.",
        )
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="L'image dépasse la limite de 10 Mo.",
        )
    width, height = inspect_image(contents)
    return ValidatedUpload(contents, width, height, media_type)
