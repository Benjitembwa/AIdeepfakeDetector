import hashlib
import io
import json
from dataclasses import dataclass
from uuid import UUID

from c2pa import Builder, Context, C2paSignerInfo, C2paSigningAlg, Reader, Signer

from app.core.config import get_settings


class C2paUnavailable(RuntimeError):
    """C2PA signing or inspection could not be completed."""


@dataclass(frozen=True)
class C2paReport:
    status: str
    active_manifest: str | None = None
    claim_generator: str | None = None
    issuer: str | None = None
    validation_codes: tuple[str, ...] = ()
    manifest_store_json: str | None = None


@dataclass(frozen=True)
class SignedC2paAsset:
    contents: bytes
    sha256: str
    report: C2paReport


def _validation_codes(store: dict[str, object]) -> tuple[str, ...]:
    values = store.get("validation_status")
    if not isinstance(values, list):
        return ()
    codes: list[str] = []
    for item in values:
        if isinstance(item, dict) and isinstance(item.get("code"), str):
            codes.append(item["code"])
    return tuple(codes)


def _report_from_store(store: dict[str, object], raw_json: str) -> C2paReport:
    active_label = store.get("active_manifest")
    manifests = store.get("manifests")
    active = (
        manifests.get(active_label)
        if isinstance(active_label, str) and isinstance(manifests, dict)
        else None
    )
    active = active if isinstance(active, dict) else {}
    signature_info = active.get("signature_info")
    signature_info = signature_info if isinstance(signature_info, dict) else {}
    claim_generator = active.get("claim_generator")
    if not isinstance(claim_generator, str):
        infos = active.get("claim_generator_info")
        first = infos[0] if isinstance(infos, list) and infos else None
        claim_generator = first.get("name") if isinstance(first, dict) else None
    issuer = signature_info.get("issuer")
    codes = _validation_codes(store)
    invalid_codes = tuple(
        code for code in codes if code != "signingCredential.untrusted"
    )
    if invalid_codes:
        status = "invalid"
    elif "signingCredential.untrusted" in codes:
        status = "valid_untrusted"
    else:
        status = "valid"
    return C2paReport(
        status=status,
        active_manifest=active_label if isinstance(active_label, str) else None,
        claim_generator=claim_generator if isinstance(claim_generator, str) else None,
        issuer=issuer if isinstance(issuer, str) else None,
        validation_codes=codes,
        manifest_store_json=raw_json,
    )


def inspect_c2pa(contents: bytes, media_type: str) -> C2paReport:
    try:
        with io.BytesIO(contents) as source:
            with Reader(media_type, source) as reader:
                raw_json = reader.json()
        store = json.loads(raw_json)
        if not isinstance(store, dict) or not store.get("active_manifest"):
            return C2paReport(status="absent")
        return _report_from_store(store, raw_json)
    except Exception as exc:
        message = str(exc).lower()
        if "manifest" in message and (
            "not found" in message or "no claim" in message or "jumbf" in message
        ):
            return C2paReport(status="absent")
        raise C2paUnavailable("La provenance C2PA n'a pas pu être analysée.") from exc


def sign_c2pa(
    contents: bytes,
    *,
    media_type: str,
    filename: str,
    image_id: UUID,
    media_name: str,
    media_slug: str,
    title: str,
    author: str,
    source_url: str | None,
    original_sha256: str,
) -> SignedC2paAsset:
    settings = get_settings()
    try:
        certificate = settings.c2pa_sign_cert_path.read_bytes()
        private_key = settings.c2pa_private_key_path.read_bytes()
    except OSError as exc:
        raise C2paUnavailable("Les identifiants C2PA ne sont pas configurés.") from exc

    manifest = {
        "title": title or filename,
        "format": media_type,
        "claim_generator_info": [{"name": "Prisme", "version": "0.1.0"}],
        "assertions": [
            {
                "label": "c2pa.actions.v2",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture",
                            "description": "Déclaration du média partenaire lors de la publication dans Prisme.",
                            "softwareAgent": {"name": "Prisme", "version": "0.1.0"},
                        }
                    ]
                },
            },
            {
                "label": "org.prisme.publisher",
                "data": {
                    "image_id": str(image_id),
                    "publisher": {"name": media_name, "slug": media_slug},
                    "title": title,
                    "author": author,
                    "source_url": source_url,
                    "original_sha256": original_sha256,
                },
            },
        ],
    }
    signer_info = C2paSignerInfo(
        alg=C2paSigningAlg.ES256,
        sign_cert=certificate,
        private_key=private_key,
        ta_url=None,
    )
    destination = io.BytesIO()
    try:
        with Context() as context:
            with Signer.from_info(signer_info) as signer:
                with Builder(json.dumps(manifest, ensure_ascii=False), context) as builder:
                    with io.BytesIO(contents) as source:
                        builder.sign(signer, media_type, source, destination)
        signed = destination.getvalue()
        report = inspect_c2pa(signed, media_type)
    except C2paUnavailable:
        raise
    except Exception as exc:
        raise C2paUnavailable("La signature C2PA a échoué.") from exc
    return SignedC2paAsset(
        contents=signed,
        sha256=hashlib.sha256(signed).hexdigest(),
        report=report,
    )
