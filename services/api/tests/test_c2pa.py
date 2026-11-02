import io
from uuid import uuid4

from PIL import Image

from app.services.c2pa_provenance import inspect_c2pa, sign_c2pa


def png_image() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 24), color=(35, 90, 70)).save(output, format="PNG")
    return output.getvalue()


def test_c2pa_asset_is_signed_and_readable() -> None:
    original = png_image()
    signed = sign_c2pa(
        original,
        media_type="image/png",
        filename="preuve.png",
        image_id=uuid4(),
        media_name="Le Journal Test",
        media_slug="le-journal-test",
        title="Preuve C2PA",
        author="Photographe Test",
        source_url="https://example.test/preuve",
        original_sha256="ab" * 32,
    )
    assert signed.contents != original
    assert signed.report.status in {"valid", "valid_untrusted"}
    assert signed.report.active_manifest
    assert signed.report.claim_generator == "Prisme"
    assert inspect_c2pa(signed.contents, "image/png").active_manifest


def test_unsigned_asset_has_no_c2pa_manifest() -> None:
    assert inspect_c2pa(png_image(), "image/png").status == "absent"
