import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ImageRecord, MediaOrganization
from app.dependencies import SessionDep
from app.schemas import (
    AiDetectionResult,
    BlockchainProvenance,
    C2paProvenance,
    VerificationImage,
    VerificationMatch,
    VerificationMedia,
    VerificationQuery,
    VerificationResponse,
)
from app.services.blockchain import RegistryUnavailable, get_registry
from app.services.c2pa_provenance import C2paUnavailable, inspect_c2pa
from app.services.image_fingerprints import compare_fingerprints, compute_fingerprint
from app.services.provenance import registry_matches_record
from app.services.sightengine import SightengineUnavailable, analyze_image
from app.services.uploads import validate_upload

router = APIRouter(prefix="/verify", tags=["Vérification publique"])


async def blockchain_provenance(record: ImageRecord) -> BlockchainProvenance:
    settings = get_settings()
    explorer_url = (
        f"{settings.base_explorer_url.rstrip('/')}/tx/{record.blockchain_tx_hash}"
        if record.blockchain_tx_hash
        else None
    )
    gateway = settings.pinata_gateway_base_url
    values = {
        "chain_id": record.blockchain_chain_id or settings.base_chain_id,
        "contract_address": record.blockchain_contract_address
        or settings.registry_contract_address,
        "transaction_hash": record.blockchain_tx_hash,
        "block_number": record.blockchain_block_number,
        "publisher_address": record.blockchain_publisher_address,
        "image_cid": record.ipfs_cid,
        "metadata_cid": record.metadata_cid,
        "image_url": f"{gateway}/ipfs/{record.ipfs_cid}"
        if gateway and record.ipfs_cid
        else None,
        "metadata_url": f"{gateway}/ipfs/{record.metadata_cid}"
        if gateway and record.metadata_cid
        else None,
        "explorer_url": explorer_url,
        "registered_at": record.blockchain_registered_at,
    }
    if not record.sha256 or not record.ipfs_cid or not record.metadata_cid:
        return BlockchainProvenance(status="not_registered", **values)
    try:
        onchain = await get_registry().get_image(record.sha256)
    except (RegistryUnavailable, ValueError):
        return BlockchainProvenance(status="unavailable", **values)
    if onchain is None:
        expected = record.status.value in {"registered", "revoked"}
        return BlockchainProvenance(
            status="mismatch" if expected else "not_registered", **values
        )
    if not registry_matches_record(onchain, record, record.media_id):
        return BlockchainProvenance(status="mismatch", **values)
    values.update(
        {
            "block_number": onchain.registered_block,
            "publisher_address": onchain.publisher,
            "image_cid": onchain.image_cid,
            "metadata_cid": onchain.metadata_cid,
            "registered_at": onchain.registered_at,
        }
    )
    return BlockchainProvenance(
        status="revoked" if onchain.revoked else "verified", **values
    )


@router.post("", response_model=VerificationResponse)
async def verify_image(
    session: SessionDep,
    image: Annotated[UploadFile, File()],
) -> VerificationResponse:
    filename = Path(image.filename or "image").name[:255] or "image"
    uploaded = await validate_upload(image)
    query = compute_fingerprint(uploaded.contents)
    settings = get_settings()

    try:
        c2pa_report = await asyncio.to_thread(
            inspect_c2pa, uploaded.contents, uploaded.media_type
        )
        c2pa_provenance = C2paProvenance(
            status=c2pa_report.status,
            active_manifest=c2pa_report.active_manifest,
            claim_generator=c2pa_report.claim_generator,
            issuer=c2pa_report.issuer,
            validation_codes=list(c2pa_report.validation_codes),
        )
    except C2paUnavailable:
        c2pa_provenance = C2paProvenance(status="unavailable")

    try:
        sightengine = await analyze_image(
            uploaded.contents,
            filename=filename,
            media_type=uploaded.media_type,
        )
        ai_detection = AiDetectionResult(
            status="evaluated",
            ai_generated_score=sightengine.ai_generated_score,
            deepfake_score=sightengine.deepfake_score,
            likely_generator=sightengine.likely_generator,
            likely_generator_score=sightengine.likely_generator_score,
            request_id=sightengine.request_id,
            operations=sightengine.operations,
        )
    except SightengineUnavailable:
        ai_detection = AiDetectionResult(status="unavailable")

    rows = (
        await session.execute(
            select(ImageRecord, MediaOrganization)
            .join(MediaOrganization, ImageRecord.media_id == MediaOrganization.id)
            .where(ImageRecord.sha256.is_not(None), MediaOrganization.is_active.is_(True))
            .order_by(ImageRecord.created_at.desc())
            .limit(settings.verification_candidate_limit)
        )
    ).all()

    matches: list[VerificationMatch] = []
    matched_records: dict[str, ImageRecord] = {}
    for record, media in rows:
        comparison = compare_fingerprints(
            query,
            stored_sha256=record.sha256,
            stored_perceptual_hash=record.perceptual_hash,
            stored_difference_hash=record.difference_hash,
            stored_wavelet_hash=record.wavelet_hash,
            stored_keypoints=record.orb_keypoints,
            stored_descriptors=record.orb_descriptors,
            stored_descriptor_count=record.orb_descriptor_count,
        )
        if comparison.matched_by is None:
            continue
        matches.append(
            VerificationMatch(
                matched_by=comparison.matched_by,
                confidence=comparison.confidence,
                perceptual_distance=comparison.perceptual_distance,
                difference_distance=comparison.difference_distance,
                wavelet_distance=comparison.wavelet_distance,
                good_matches=comparison.good_matches,
                inliers=comparison.inliers,
                media=VerificationMedia(id=media.id, name=media.name, slug=media.slug),
                image=VerificationImage.model_validate(record, from_attributes=True),
                registry=BlockchainProvenance(
                    status="not_registered",
                    chain_id=settings.base_chain_id,
                    contract_address=settings.registry_contract_address,
                ),
            )
        )
        matched_records[str(record.id)] = record

    matches.sort(
        key=lambda match: (match.matched_by == "exact", match.confidence), reverse=True
    )
    top_matches = matches[:5]
    for index, match in enumerate(top_matches):
        record = matched_records[str(match.image.id)]
        top_matches[index] = match.model_copy(
            update={"registry": await blockchain_provenance(record)}
        )
    return VerificationResponse(
        query=VerificationQuery(
            filename=filename,
            size_bytes=len(uploaded.contents),
            width=uploaded.width,
            height=uploaded.height,
            sha256=query.sha256,
        ),
        match_count=len(matches),
        matches=top_matches,
        ai_detection=ai_detection,
        c2pa_provenance=c2pa_provenance,
        limitation=(
            "Une correspondance indique un lien visuel avec un enregistrement partenaire ; "
            "elle ne prouve ni le contexte ni la véracité de la scène."
        ),
    )
