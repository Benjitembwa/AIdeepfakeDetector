import io
from typing import Any

from httpx import AsyncClient
from PIL import Image, ImageDraw

from app.services.blockchain import TransactionOutcome


def png_file() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (16, 12), color=(34, 94, 78)).save(output, format="PNG")
    return output.getvalue()


def scene_file(
    *, image_format: str = "PNG", quality: int = 90, crop: bool = False
) -> bytes:
    image = Image.new("RGB", (480, 360), color=(232, 223, 195))
    draw = ImageDraw.Draw(image)
    for x in range(0, 480, 32):
        draw.line((x, 0, 479 - x // 3, 359), fill=(30 + x % 180, 60, 110), width=3)
    for y in range(0, 360, 30):
        draw.rectangle((20 + y // 3, y, 95 + y // 2, y + 18), outline=(18, 96, 77), width=3)
    draw.ellipse((155, 70, 315, 230), fill=(222, 126, 74), outline=(35, 45, 70), width=7)
    draw.polygon([(65, 315), (205, 170), (355, 315)], fill=(51, 92, 82), outline="white")
    draw.text((175, 115), "PRISME 2026", fill="white", stroke_width=1, stroke_fill="black")
    if crop:
        image = image.crop((55, 40, 430, 330)).resize((480, 360))
    output = io.BytesIO()
    options = {"quality": quality} if image_format == "JPEG" else {}
    image.save(output, format=image_format, **options)
    return output.getvalue()


async def register(
    client: AsyncClient,
    *,
    name: str = "Le Journal Test",
    email: str = "redaction@prisme.fr",
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": name,
            "email": email,
            "password": "mot-de-passe-test-123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_health_registration_login_and_current_media(client: AsyncClient) -> None:
    health = await client.get("/health/ready")
    assert health.status_code == 200
    assert health.json()["database"] == "connected"

    registration = await register(client)
    assert registration["media"]["name"] == "Le Journal Test"
    token = registration["access_token"]

    current = await client.get(
        "/api/v1/media/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current.status_code == 200
    assert current.json()["email"] == "redaction@prisme.fr"

    login = await client.post(
        "/api/v1/auth/token",
        data={"username": "redaction@prisme.fr", "password": "mot-de-passe-test-123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


async def test_duplicate_and_bad_credentials_are_rejected(client: AsyncClient) -> None:
    await register(client)
    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Un autre nom",
            "email": "redaction@prisme.fr",
            "password": "autre-mot-de-passe-123",
        },
    )
    assert duplicate.status_code == 409

    bad_login = await client.post(
        "/api/v1/auth/token",
        data={"username": "redaction@prisme.fr", "password": "mot-de-passe-incorrect"},
    )
    assert bad_login.status_code == 401
    assert "password" not in bad_login.text.lower()


async def test_image_publication_revocation_and_media_isolation(client: AsyncClient) -> None:
    first = await register(client)
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    created = await client.post(
        "/api/v1/images",
        headers=first_headers,
        data={
            "title": "Le marché au matin",
            "author": "Camille Test",
            "license": "Tous droits réservés",
            "source_url": "https://example.test/reportage",
            "description": "Contexte du reportage.",
        },
        files={"image": ("marche.png", png_file(), "image/png")},
    )
    assert created.status_code == 201, created.text
    image = created.json()
    assert image["width"] == 16
    assert image["height"] == 12
    assert image["status"] == "registered"
    assert len(image["sha256"]) == 64
    assert len(image["perceptual_hash"]) == 16
    assert image["fingerprint_version"] == 1
    assert image["ipfs_cid"].startswith("bafy-")
    assert image["metadata_cid"].startswith("bafy-")
    assert image["blockchain_chain_id"] == 84532
    assert image["blockchain_block_number"] > 0

    listing = await client.get("/api/v1/images?search=marché", headers=first_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    second = await register(
        client, name="Regards Test", email="regards@prisme.fr"
    )
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    hidden = await client.get(f"/api/v1/images/{image['id']}", headers=second_headers)
    assert hidden.status_code == 404

    deleted = await client.delete(f"/api/v1/images/{image['id']}", headers=first_headers)
    assert deleted.status_code == 204
    archived = await client.get("/api/v1/images", headers=first_headers)
    assert archived.json()["total"] == 1
    assert archived.json()["items"][0]["status"] == "revoked"
    assert archived.json()["items"][0]["revocation_tx_hash"]


async def test_invalid_upload_is_rejected(client: AsyncClient) -> None:
    account = await register(client)
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    response = await client.post(
        "/api/v1/images",
        headers=headers,
        data={"title": "Faux", "author": "Test", "license": "CC0"},
        files={"image": ("texte.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 415


async def test_registered_image_is_recognized_exactly_and_after_transformations(
    client: AsyncClient,
) -> None:
    account = await register(client)
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    original = scene_file()
    created = await client.post(
        "/api/v1/images",
        headers=headers,
        data={
            "title": "La place au matin",
            "author": "Amina Exemple",
            "license": "CC BY 4.0",
            "source_url": "https://example.test/place",
        },
        files={"image": ("place.png", original, "image/png")},
    )
    assert created.status_code == 201, created.text
    assert created.json()["orb_descriptor_count"] > 20

    exact = await client.post(
        "/api/v1/verify", files={"image": ("copie.png", original, "image/png")}
    )
    assert exact.status_code == 200, exact.text
    exact_payload = exact.json()
    assert exact_payload["match_count"] == 1
    assert exact_payload["matches"][0]["matched_by"] == "exact"
    assert exact_payload["matches"][0]["confidence"] == 1
    assert exact_payload["matches"][0]["media"]["name"] == "Le Journal Test"
    assert exact_payload["matches"][0]["registry"]["status"] == "verified"
    assert exact_payload["ai_detection"] == {
        "status": "evaluated",
        "provider": "sightengine",
        "ai_generated_score": 0.87,
        "deepfake_score": 0.08,
        "likely_generator": "midjourney",
        "likely_generator_score": 0.72,
        "request_id": "req_test",
        "operations": 6,
    }

    recompressed = await client.post(
        "/api/v1/verify",
        files={"image": ("place-recompressee.jpg", scene_file(image_format="JPEG", quality=55), "image/jpeg")},
    )
    assert recompressed.status_code == 200, recompressed.text
    assert recompressed.json()["matches"][0]["matched_by"] in {
        "perceptual",
        "local_features",
    }

    cropped = await client.post(
        "/api/v1/verify",
        files={"image": ("place-recadree.jpg", scene_file(image_format="JPEG", quality=70, crop=True), "image/jpeg")},
    )
    assert cropped.status_code == 200, cropped.text
    assert cropped.json()["matches"][0]["matched_by"] in {
        "perceptual",
        "local_features",
    }

    unrelated = await client.post(
        "/api/v1/verify", files={"image": ("autre.png", png_file(), "image/png")}
    )
    assert unrelated.status_code == 200
    assert unrelated.json()["match_count"] == 0


async def test_pending_registration_is_retried_idempotently(
    client: AsyncClient,
    external_services_stub: dict[str, object],
) -> None:
    account = await register(client)
    headers = {"Authorization": f"Bearer {account['access_token']}"}
    registry: Any = external_services_stub["registry"]
    registry.next_registration_state = "pending"

    created = await client.post(
        "/api/v1/images",
        headers=headers,
        data={"title": "Preuve en attente", "author": "Test", "license": "CC0"},
        files={"image": ("pending.png", png_file(), "image/png")},
    )
    assert created.status_code == 202
    payload = created.json()
    assert payload["status"] == "blockchain_pending"
    assert registry.counter == 1

    still_pending = await client.post(
        f"/api/v1/images/{payload['id']}/retry-registration", headers=headers
    )
    assert still_pending.status_code == 202
    assert registry.counter == 1

    registry.transactions[payload["blockchain_tx_hash"]] = TransactionOutcome(
        state="failed", tx_hash=payload["blockchain_tx_hash"]
    )
    registry.next_registration_state = "confirmed"
    confirmed = await client.post(
        f"/api/v1/images/{payload['id']}/retry-registration", headers=headers
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "registered"
    assert registry.counter == 2

    reconciled = await client.post(
        f"/api/v1/images/{payload['id']}/retry-registration", headers=headers
    )
    assert reconciled.status_code == 200
    assert registry.counter == 2

    duplicate = await client.post(
        "/api/v1/images",
        headers=headers,
        data={"title": "Doublon", "author": "Test", "license": "CC0"},
        files={"image": ("duplicate.png", png_file(), "image/png")},
    )
    assert duplicate.status_code == 409
