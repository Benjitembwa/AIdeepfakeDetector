import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SightengineUnavailable(RuntimeError):
    """L'analyse externe n'a pas pu produire de résultat exploitable."""


@dataclass(frozen=True)
class SightengineResult:
    ai_generated_score: float
    deepfake_score: float
    likely_generator: str | None
    likely_generator_score: float | None
    request_id: str | None
    operations: int | None


def _score(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SightengineUnavailable(f"Score Sightengine absent : {field}")
    score = float(value)
    if not 0 <= score <= 1:
        raise SightengineUnavailable(f"Score Sightengine invalide : {field}")
    return score


def parse_sightengine_response(payload: dict[str, Any]) -> SightengineResult:
    if payload.get("status") != "success":
        raise SightengineUnavailable("Sightengine a refusé l'analyse")
    type_scores = payload.get("type")
    if not isinstance(type_scores, dict):
        raise SightengineUnavailable("Réponse Sightengine incomplète")

    generators = type_scores.get("ai_generators")
    valid_generators: list[tuple[str, float]] = []
    if isinstance(generators, dict):
        for name, value in generators.items():
            if isinstance(name, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric = float(value)
                if 0 <= numeric <= 1:
                    valid_generators.append((name, numeric))
    likely_generator, likely_generator_score = (
        max(valid_generators, key=lambda item: item[1])
        if valid_generators
        else (None, None)
    )

    request = payload.get("request")
    request_id = request.get("id") if isinstance(request, dict) else None
    operations = request.get("operations") if isinstance(request, dict) else None
    return SightengineResult(
        ai_generated_score=_score(type_scores.get("ai_generated"), "ai_generated"),
        deepfake_score=_score(type_scores.get("deepfake"), "deepfake"),
        likely_generator=likely_generator,
        likely_generator_score=likely_generator_score,
        request_id=request_id if isinstance(request_id, str) else None,
        operations=operations if isinstance(operations, int) and not isinstance(operations, bool) else None,
    )


async def analyze_image(
    contents: bytes,
    *,
    filename: str,
    media_type: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SightengineResult:
    settings = get_settings()
    if settings.sightengine_api_user is None or settings.sightengine_api_secret is None:
        raise SightengineUnavailable("Identifiants Sightengine absents")

    data = {
        "models": "genai,deepfake",
        "api_user": settings.sightengine_api_user.get_secret_value(),
        "api_secret": settings.sightengine_api_secret.get_secret_value(),
    }
    files = {"media": (filename, contents, media_type)}
    try:
        async with httpx.AsyncClient(
            timeout=settings.sightengine_timeout_seconds,
            transport=transport,
        ) as client:
            response = await client.post(settings.sightengine_api_url, data=data, files=files)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("L'appel Sightengine a échoué (%s)", type(exc).__name__)
        raise SightengineUnavailable("Sightengine est temporairement indisponible") from exc
    if not isinstance(payload, dict):
        raise SightengineUnavailable("Réponse Sightengine invalide")
    return parse_sightengine_response(payload)
