import hashlib
import json
from uuid import UUID

from app.db.models import ImageRecord, MediaOrganization
from app.services.blockchain import RegistryRecord

METADATA_SCHEMA_VERSION = "prisme-image-metadata/1.0"


def media_id_digest(media_id: UUID) -> bytes:
    return hashlib.sha256(media_id.bytes).digest()


def canonical_metadata(
    record: ImageRecord,
    media: MediaOrganization,
    *,
    image_cid: str,
) -> tuple[bytes, str]:
    payload = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "image": {
            "id": str(record.id),
            "title": record.title,
            "author": record.author,
            "source_url": record.source_url,
            "license": record.license,
            "description": record.description,
            "original_filename": record.original_filename,
            "media_type": record.media_type,
            "size_bytes": record.size_bytes,
            "width": record.width,
            "height": record.height,
            "sha256": record.sha256,
            "perceptual_hash": record.perceptual_hash,
            "difference_hash": record.difference_hash,
            "wavelet_hash": record.wavelet_hash,
            "fingerprint_version": record.fingerprint_version,
        },
        "publisher": {
            "name": media.name,
            "slug": media.slug,
            "media_id_hash": media_id_digest(media.id).hex(),
            "wallet_address": record.blockchain_publisher_address,
        },
        "storage": {"network": "ipfs", "image_cid": image_cid},
        "c2pa": {
            "status": record.c2pa_status,
            "active_manifest": record.c2pa_active_manifest,
            "claim_generator": record.c2pa_claim_generator,
            "issuer": record.c2pa_issuer,
            "signed_asset_sha256": record.c2pa_asset_sha256,
            "signed_asset_size_bytes": record.c2pa_asset_size_bytes,
        },
        "created_at": record.created_at.isoformat(),
    }
    contents = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return contents, hashlib.sha256(contents).hexdigest()


def registry_matches_record(
    onchain: RegistryRecord,
    record: ImageRecord,
    media_id: UUID,
) -> bool:
    required = (
        record.metadata_sha256,
        record.perceptual_hash,
        record.difference_hash,
        record.wavelet_hash,
        record.ipfs_cid,
        record.metadata_cid,
    )
    if any(value is None for value in required):
        return False
    return (
        onchain.media_id == media_id_digest(media_id)
        and onchain.metadata_sha256.hex() == record.metadata_sha256
        and onchain.perceptual_hash == int(record.perceptual_hash, 16)
        and onchain.difference_hash == int(record.difference_hash, 16)
        and onchain.wavelet_hash == int(record.wavelet_hash, 16)
        and onchain.image_cid == record.ipfs_cid
        and onchain.metadata_cid == record.metadata_cid
    )
