import httpx
import pytest

from app.services.pinata import PinataClient, PinataUnavailable


async def test_pinata_upload_uses_jwt_public_cidv1_and_returns_identifiers() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-pinata-jwt"
        assert request.url == "https://uploads.pinata.cloud/v3/files"
        body = await request.aread()
        assert b'name="network"' in body and b"public" in body
        assert b'name="cid_version"' in body and b"v1" in body
        assert b'filename="preuve.png"' in body
        return httpx.Response(
            200,
            json={"data": {"id": "file-123", "cid": "bafy-public-cid"}},
        )

    result = await PinataClient(transport=httpx.MockTransport(handler)).upload_public(
        b"image-bytes",
        filename="preuve.png",
        media_type="image/png",
        keyvalues={"kind": "image"},
    )
    assert result.file_id == "file-123"
    assert result.cid == "bafy-public-cid"


async def test_pinata_delete_is_idempotent_for_a_missing_file() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/v3/files/public/file-absent"
        return httpx.Response(404)

    await PinataClient(transport=httpx.MockTransport(handler)).delete_public(
        "file-absent"
    )


async def test_pinata_errors_do_not_expose_the_jwt() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="token rejected")

    with pytest.raises(PinataUnavailable) as caught:
        await PinataClient(transport=httpx.MockTransport(handler)).upload_public(
            b"x",
            filename="preuve.png",
            media_type="image/png",
            keyvalues={},
        )
    assert "test-pinata-jwt" not in str(caught.value)
