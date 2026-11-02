import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select

from app.core.config import get_settings
from app.db.models import ImageRecord, ImageStatus
from app.dependencies import CurrentMediaDep, SessionDep
from app.schemas import ImageMetadata, ImagePage, ImagePublic
from app.services.blockchain import (
    BlockchainRegistry,
    RegistryUnavailable,
    TransactionOutcome,
    get_registry,
)
from app.services.c2pa_provenance import C2paUnavailable, sign_c2pa
from app.services.image_fingerprints import FINGERPRINT_VERSION, compute_fingerprint
from app.services.pinata import PinataClient, PinataUnavailable, get_pinata_client
from app.services.provenance import canonical_metadata, media_id_digest, registry_matches_record
from app.services.uploads import validate_upload

router = APIRouter(prefix="/images", tags=["Images"])


def _technical_error(exc: Exception) -> str:
    """Store a useful category without leaking a secret or an upstream response."""
    return f"{type(exc).__name__}: opération externe non aboutie"[:500]


def _apply_chain_identity(record: ImageRecord, registry: BlockchainRegistry) -> None:
    settings = get_settings()
    record.blockchain_chain_id = settings.base_chain_id
    record.blockchain_contract_address = registry.contract_address
    record.blockchain_publisher_address = registry.publisher_address


async def _mark_registered(
    record: ImageRecord,
    registry: BlockchainRegistry,
    outcome: TransactionOutcome,
) -> None:
    record.status = ImageStatus.REGISTERED
    record.blockchain_tx_hash = outcome.tx_hash
    record.blockchain_block_number = outcome.block_number
    record.blockchain_registered_at = datetime.now(UTC)
    record.registration_error = None
    try:
        onchain = await registry.get_image(record.sha256 or "")
    except RegistryUnavailable:
        onchain = None
    if onchain is not None:
        record.blockchain_block_number = onchain.registered_block
        record.blockchain_registered_at = onchain.registered_at
        record.blockchain_publisher_address = onchain.publisher


async def _register_record(
    record: ImageRecord,
    registry: BlockchainRegistry,
) -> TransactionOutcome:
    required = (
        record.sha256,
        record.perceptual_hash,
        record.difference_hash,
        record.wavelet_hash,
        record.ipfs_cid,
        record.metadata_cid,
        record.metadata_sha256,
    )
    if any(value is None for value in required):
        raise RegistryUnavailable("Les preuves à enregistrer sont incomplètes.")
    _apply_chain_identity(record, registry)
    outcome = await registry.register_image(
        image_sha256=record.sha256 or "",
        perceptual_hash=record.perceptual_hash or "",
        difference_hash=record.difference_hash or "",
        wavelet_hash=record.wavelet_hash or "",
        image_cid=record.ipfs_cid or "",
        metadata_cid=record.metadata_cid or "",
        metadata_sha256=record.metadata_sha256 or "",
        media_id=media_id_digest(record.media_id),
    )
    record.blockchain_tx_hash = outcome.tx_hash
    if outcome.state == "confirmed":
        await _mark_registered(record, registry, outcome)
    elif outcome.state == "pending":
        record.status = ImageStatus.BLOCKCHAIN_PENDING
        record.registration_error = None
    else:
        record.status = ImageStatus.REGISTRATION_FAILED
        record.registration_error = "La transaction blockchain a échoué."
    return outcome


async def _unpin_record(record: ImageRecord, pinata: PinataClient) -> list[str]:
    errors: list[str] = []
    for attribute in ("metadata_ipfs_file_id", "ipfs_file_id"):
        file_id = getattr(record, attribute)
        if not file_id:
            continue
        try:
            await pinata.delete_public(file_id)
            setattr(record, attribute, None)
        except PinataUnavailable as exc:
            errors.append(_technical_error(exc))
    return errors


@router.get("", response_model=ImagePage)
async def list_images(
    session: SessionDep,
    media: CurrentMediaDep,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ImagePage:
    filters = [ImageRecord.media_id == media.id]
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                ImageRecord.title.ilike(pattern),
                ImageRecord.author.ilike(pattern),
                ImageRecord.original_filename.ilike(pattern),
            )
        )
    total = await session.scalar(select(func.count(ImageRecord.id)).where(*filters))
    records = (
        await session.scalars(
            select(ImageRecord)
            .where(*filters)
            .order_by(ImageRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return ImagePage(
        items=[ImagePublic.model_validate(record) for record in records],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ImagePublic, status_code=status.HTTP_201_CREATED)
async def create_image(
    response: Response,
    session: SessionDep,
    media: CurrentMediaDep,
    image: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=150)],
    author: Annotated[str, Form(min_length=1, max_length=100)],
    license: Annotated[str, Form(min_length=1, max_length=80)],
    source_url: Annotated[str | None, Form(max_length=500)] = None,
    description: Annotated[str | None, Form(max_length=1200)] = None,
) -> ImageRecord:
    uploaded = await validate_upload(image)
    fingerprint = compute_fingerprint(uploaded.contents)
    try:
        metadata = ImageMetadata.model_validate(
            {
                "title": title,
                "author": author,
                "license": license,
                "source_url": source_url or None,
                "description": description,
            }
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(include_url=False, include_input=False),
        ) from exc

    existing = await session.scalar(
        select(ImageRecord).where(ImageRecord.sha256 == fingerprint.sha256).limit(1)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette image possède déjà un enregistrement local. Utilisez la reprise si nécessaire.",
        )

    registry = get_registry()
    try:
        await registry.validate_configuration()
        if await registry.exists(fingerprint.sha256):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cette empreinte SHA-256 existe déjà dans le registre Base Sepolia.",
            )
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    filename = Path(image.filename or "image").name[:255] or "image"
    image_id = uuid4()
    try:
        signed_asset = await asyncio.to_thread(
            sign_c2pa,
            uploaded.contents,
            media_type=uploaded.media_type,
            filename=filename,
            image_id=image_id,
            media_name=media.name,
            media_slug=media.slug,
            title=metadata.title,
            author=metadata.author,
            source_url=str(metadata.source_url) if metadata.source_url else None,
            original_sha256=fingerprint.sha256,
        )
    except C2paUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    now = datetime.now(UTC)
    record = ImageRecord(
        id=image_id,
        media_id=media.id,
        title=metadata.title,
        author=metadata.author,
        source_url=str(metadata.source_url) if metadata.source_url else None,
        license=metadata.license,
        description=metadata.description,
        original_filename=filename,
        media_type=uploaded.media_type,
        size_bytes=len(uploaded.contents),
        width=uploaded.width,
        height=uploaded.height,
        status=ImageStatus.FINGERPRINTED,
        sha256=fingerprint.sha256,
        perceptual_hash=fingerprint.perceptual_hash,
        difference_hash=fingerprint.difference_hash,
        wavelet_hash=fingerprint.wavelet_hash,
        fingerprint_version=FINGERPRINT_VERSION,
        orb_keypoints=fingerprint.orb_keypoints,
        orb_descriptors=fingerprint.orb_descriptors,
        orb_descriptor_count=fingerprint.orb_descriptor_count,
        c2pa_status=signed_asset.report.status,
        c2pa_active_manifest=signed_asset.report.active_manifest,
        c2pa_claim_generator=signed_asset.report.claim_generator,
        c2pa_issuer=signed_asset.report.issuer,
        c2pa_validation_codes=json.dumps(signed_asset.report.validation_codes),
        c2pa_manifest=signed_asset.report.manifest_store_json,
        c2pa_asset_sha256=signed_asset.sha256,
        c2pa_asset_size_bytes=len(signed_asset.contents),
        created_at=now,
        updated_at=now,
    )
    pinata = get_pinata_client()
    image_file = None
    try:
        image_file = await pinata.upload_public(
            signed_asset.contents,
            filename=filename,
            media_type=uploaded.media_type,
            keyvalues={"kind": "image", "image_id": str(record.id), "media_id": str(media.id)},
        )
        record.ipfs_cid = image_file.cid
        record.ipfs_file_id = image_file.file_id
        metadata_contents, metadata_sha256 = canonical_metadata(
            record, media, image_cid=image_file.cid
        )
        metadata_file = await pinata.upload_public(
            metadata_contents,
            filename=f"{record.id}.json",
            media_type="application/json",
            keyvalues={"kind": "metadata", "image_id": str(record.id), "media_id": str(media.id)},
        )
    except PinataUnavailable as exc:
        if image_file is not None:
            try:
                await pinata.delete_public(image_file.file_id)
            except PinataUnavailable:
                pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    record.metadata_cid = metadata_file.cid
    record.metadata_ipfs_file_id = metadata_file.file_id
    record.metadata_sha256 = metadata_sha256
    record.status = ImageStatus.IPFS_STORED
    session.add(record)
    await session.commit()
    await session.refresh(record)

    try:
        outcome = await _register_record(record, registry)
        if outcome.state != "confirmed":
            response.status_code = status.HTTP_202_ACCEPTED
    except RegistryUnavailable as exc:
        record.status = ImageStatus.REGISTRATION_FAILED
        record.registration_error = _technical_error(exc)
        response.status_code = status.HTTP_202_ACCEPTED
    await session.commit()
    await session.refresh(record)
    return record


async def owned_image_or_404(
    image_id: UUID, media_id: UUID, session: SessionDep
) -> ImageRecord:
    record = await session.scalar(
        select(ImageRecord).where(
            ImageRecord.id == image_id,
            ImageRecord.media_id == media_id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image introuvable.",
        )
    return record


@router.get("/{image_id}", response_model=ImagePublic)
async def read_image(
    image_id: UUID, session: SessionDep, media: CurrentMediaDep
) -> ImageRecord:
    return await owned_image_or_404(image_id, media.id, session)


@router.post("/{image_id}/retry-registration", response_model=ImagePublic)
async def retry_registration(
    image_id: UUID,
    response: Response,
    session: SessionDep,
    media: CurrentMediaDep,
) -> ImageRecord:
    record = await owned_image_or_404(image_id, media.id, session)
    if record.status == ImageStatus.REVOKED:
        raise HTTPException(status_code=409, detail="Une preuve révoquée ne peut pas être réenregistrée.")
    if not record.ipfs_cid or not record.metadata_cid:
        raise HTTPException(status_code=409, detail="Les preuves IPFS sont incomplètes.")

    registry = get_registry()
    try:
        await registry.validate_configuration()
        _apply_chain_identity(record, registry)
        if record.blockchain_tx_hash:
            receipt = await registry.transaction_receipt(record.blockchain_tx_hash)
            if receipt.state == "pending":
                record.status = ImageStatus.BLOCKCHAIN_PENDING
                response.status_code = status.HTTP_202_ACCEPTED
                await session.commit()
                await session.refresh(record)
                return record

        onchain = await registry.get_image(record.sha256 or "")
        if onchain is not None:
            if not registry_matches_record(onchain, record, record.media_id):
                raise HTTPException(status_code=409, detail="La preuve on-chain diverge des données locales.")
            if onchain.revoked:
                record.status = ImageStatus.REVOKED
                record.revoked_at = record.revoked_at or datetime.now(UTC)
                await session.commit()
                raise HTTPException(status_code=409, detail="La preuve on-chain est déjà révoquée.")
            outcome = TransactionOutcome(
                state="confirmed",
                tx_hash=record.blockchain_tx_hash or "",
                block_number=onchain.registered_block,
            )
            await _mark_registered(record, registry, outcome)
        else:
            outcome = await _register_record(record, registry)
            if outcome.state != "confirmed":
                response.status_code = status.HTTP_202_ACCEPTED
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        record.status = ImageStatus.REGISTRATION_FAILED
        record.registration_error = _technical_error(exc)
        response.status_code = status.HTTP_202_ACCEPTED

    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    response: Response,
    session: SessionDep,
    media: CurrentMediaDep,
) -> None:
    record = await owned_image_or_404(image_id, media.id, session)
    pinata = get_pinata_client()
    has_ipfs = bool(record.ipfs_file_id or record.metadata_ipfs_file_id)

    if not has_ipfs and record.status in {ImageStatus.DRAFT, ImageStatus.FINGERPRINTED}:
        await session.delete(record)
        await session.commit()
        return

    registry = get_registry()
    try:
        await registry.validate_configuration()
        if record.revocation_tx_hash:
            receipt = await registry.transaction_receipt(record.revocation_tx_hash)
            if receipt.state == "pending":
                response.status_code = status.HTTP_202_ACCEPTED
                await session.commit()
                return
        onchain = await registry.get_image(record.sha256 or "")
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if onchain is not None and not registry_matches_record(onchain, record, record.media_id):
        raise HTTPException(status_code=409, detail="La preuve on-chain diverge des données locales.")

    if onchain is not None and not onchain.revoked:
        outcome = await registry.revoke_image(record.sha256 or "")
        record.revocation_tx_hash = outcome.tx_hash
        if outcome.state == "pending":
            response.status_code = status.HTTP_202_ACCEPTED
            record.registration_error = None
            await session.commit()
            return
        if outcome.state != "confirmed":
            record.registration_error = "La transaction de révocation a échoué."
            await session.commit()
            raise HTTPException(status_code=502, detail=record.registration_error)

    if onchain is not None:
        record.status = ImageStatus.REVOKED
        record.revoked_at = datetime.now(UTC)
        errors = await _unpin_record(record, pinata)
        record.registration_error = "; ".join(errors) or None
        await session.commit()
        return

    errors = await _unpin_record(record, pinata)
    if errors:
        record.status = ImageStatus.REGISTRATION_FAILED
        record.registration_error = "; ".join(errors)
        await session.commit()
        raise HTTPException(status_code=502, detail="Le désépinglage IPFS est incomplet.")
    await session.delete(record)
    await session.commit()
