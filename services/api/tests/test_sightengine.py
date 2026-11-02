import json

import httpx
import pytest

from app.services.sightengine import (
    SightengineUnavailable,
    analyze_image,
    parse_sightengine_response,
)


def sightengine_payload() -> dict[str, object]:
    return {
        "status": "success",
        "request": {"id": "req_123", "operations": 6},
        "type": {
            "ai_generated": 0.91,
            "deepfake": 0.12,
            "ai_generators": {"midjourney": 0.81, "flux": 0.25},
        },
    }


def test_sightengine_response_is_normalized() -> None:
    result = parse_sightengine_response(sightengine_payload())
    assert result.ai_generated_score == 0.91
    assert result.deepfake_score == 0.12
    assert result.likely_generator == "midjourney"
    assert result.likely_generator_score == 0.81
    assert result.request_id == "req_123"
    assert result.operations == 6


def test_invalid_sightengine_response_is_rejected() -> None:
    with pytest.raises(SightengineUnavailable):
        parse_sightengine_response({"status": "failure"})
    with pytest.raises(SightengineUnavailable):
        parse_sightengine_response(
            {"status": "success", "type": {"ai_generated": 1.5, "deepfake": 0.1}}
        )


async def test_sightengine_request_contains_models_and_image() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert request.url == "https://api.sightengine.com/1.0/check.json"
        assert b'genai,deepfake' in body
        assert b'photo.png' in body
        assert b'fake-image-bytes' in body
        return httpx.Response(200, content=json.dumps(sightengine_payload()))

    result = await analyze_image(
        b"fake-image-bytes",
        filename="photo.png",
        media_type="image/png",
        transport=httpx.MockTransport(handler),
    )
    assert result.ai_generated_score == 0.91
