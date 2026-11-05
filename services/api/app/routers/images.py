import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from web3 import Web3

from app.core.config import get_settings
from app.db.models import ImageRecord, ImageStatus
from app.dependencies import CurrentMediaDep, SessionDep
from app.schemas import (
    ImageMetadata,
    ImagePage,
    ImagePublic,
    TransactionConfirmation,
    WalletActionResponse,
    WalletTransactionPublic,
)
from app.services.blockchain import (
    BlockchainRegistry,
    RegistryUnavailable,
    WalletTransaction,
    get_registry,
)
from app.services.c2pa_provenance import C2paUnavailable, sign_c2pa
from app.services.image_fingerprints import FINGERPRINT_VERSION, compute_fingerprint
from app.services.pinata import PinataClient, PinataUnavailable, get_pinata_client
from app.services.provenance import canonical_metadata, media_id_digest, registry_matches_record
from app.services.uploads import validate_upload

router = APIRouter(prefix="/images", tags=["Images"])


def _technical_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: opération externe non aboutie"[:500]


def _normalize_wallet(value: str) -> str:
    try:
        return Web3.to_checksum_address(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Adresse de portefeuille invalide.") from exc


def _apply_chain_identity(
    record: ImageRecord,
    registry: BlockchainRegistry,
    publisher_address: str | None = None,
) -> None:
    record.blockchain_chain_id = get_settings().base_chain_id
    record.blockchain_contract_address = registry.contract_address
    if publisher_address is not None:
        record.blockchain_publisher_address = _normalize_wallet(publisher_address)


def _public_transaction(transaction: WalletTransaction | None) -> WalletTransactionPublic | None:
    if transaction is None:
        return None
    return WalletTransactionPublic(**transaction.__dict__)


def _wallet_action(
    record: ImageRecord, transaction: WalletTransaction | None = None
) -> WalletActionResponse:
    return WalletActionResponse(
        image=ImagePublic.model_validate(record),
        transaction=_public_transaction(transaction),
    )


def _registration_transaction(
    record: ImageRecord, registry: BlockchainRegistry
) -> WalletTransaction:
    required = (
        record.sha256,
        record.perceptual_hash,
        record.difference_hash,
        record.wavelet_hash,
        record.ipfs_cid,
        record.metadata_cid,
        record.metadata_sha256,
        record.blockchain_publisher_address,
    )
    if any(value is None for value in required):
        raise HTTPException(status_code=409, detail="Les preuves à enregistrer sont incomplètes.")
    return registry.registration_transaction(
        image_sha256=record.sha256 or "",
        perceptual_hash=record.perceptual_hash or "",
        difference_hash=record.difference_hash or "",
        wavelet_hash=record.wavelet_hash or "",
        image_cid=record.ipfs_cid or "",
        metadata_cid=record.metadata_cid or "",
        metadata_sha256=record.metadata_sha256 or "",
        media_id=media_id_digest(record.media_id),
        publisher_address=record.blockchain_publisher_address or "",
    )


async def _mark_registered(
    record: ImageRecord,
    registry: BlockchainRegistry,
    *,
    tx_hash: str | None,
) -> None:
    onchain = await registry.get_image(record.sha256 or "")
    if onchain is None:
        raise HTTPException(status_code=409, detail="La preuve n'existe pas dans le contrat.")
    if not registry_matches_record(onchain, record, record.media_id):
        raise HTTPException(status_code=409, detail="La preuve on-chain diverge des données locales.")
    expected = _normalize_wallet(record.blockchain_publisher_address or "")
    if Web3.to_checksum_address(onchain.publisher) != expected:
        raise HTTPException(
            status_code=409,
            detail="La preuve a été enregistrée par un autre portefeuille.",
        )
    if onchain.revoked:
        record.status = ImageStatus.REVOKED
        record.revoked_at = record.revoked_at or datetime.now(UTC)
        return
    record.status = ImageStatus.REGISTERED
    if tx_hash:
        record.blockchain_tx_hash = tx_hash
    record.blockchain_block_number = onchain.registered_block
    record.blockchain_registered_at = onchain.registered_at
    record.blockchain_publisher_address = onchain.publisher
    record.registration_error = None


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


async def _finish_revocation(record: ImageRecord, pinata: PinataClient) -> None:
    record.status = ImageStatus.REVOKED
    record.revoked_at = record.revoked_at or datetime.now(UTC)
    errors = await _unpin_record(record, pinata)
    record.registration_error = "; ".join(errors) or None


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


@router.post("", response_model=WalletActionResponse, status_code=status.HTTP_201_CREATED)
async def create_image(
    session: SessionDep,
    media: CurrentMediaDep,
    image: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=150)],
    author: Annotated[str, Form(min_length=1, max_length=100)],
    license: Annotated[str, Form(min_length=1, max_length=80)],
    wallet_address: Annotated[str, Form(min_length=42, max_length=42)],
    source_url: Annotated[str | None, Form(max_length=500)] = None,
    description: Annotated[str | None, Form(max_length=1200)] = None,
) -> WalletActionResponse:
    publisher_address = _normalize_wallet(wallet_address)
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
            status_code=409,
            detail="Cette image possède déjà un enregistrement local. Utilisez la reprise.",
        )

    registry = get_registry()
    try:
        await registry.validate_configuration()
        if await registry.exists(fingerprint.sha256):
            raise HTTPException(
                status_code=409,
                detail="Cette empreinte SHA-256 existe déjà dans le registre Base Sepolia.",
            )
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
    _apply_chain_identity(record, registry, publisher_address)
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
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    record.metadata_cid = metadata_file.cid
    record.metadata_ipfs_file_id = metadata_file.file_id
    record.metadata_sha256 = metadata_sha256
    record.status = ImageStatus.IPFS_STORED
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return _wallet_action(record, _registration_transaction(record, registry))


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
        raise HTTPException(status_code=404, detail="Image introuvable.")
    return record


@router.get("/{image_id}", response_model=ImagePublic)
async def read_image(
    image_id: UUID, session: SessionDep, media: CurrentMediaDep
) -> ImageRecord:
    return await owned_image_or_404(image_id, media.id, session)


@router.post("/{image_id}/prepare-registration", response_model=WalletActionResponse)
async def prepare_registration(
    image_id: UUID,
    session: SessionDep,
    media: CurrentMediaDep,
) -> WalletActionResponse:
    record = await owned_image_or_404(image_id, media.id, session)
    if record.status == ImageStatus.REVOKED:
        raise HTTPException(status_code=409, detail="Une preuve révoquée ne peut pas être réenregistrée.")
    registry = get_registry(record.blockchain_contract_address)
    try:
        await registry.validate_configuration()
        _apply_chain_identity(record, registry)
        expected = _registration_transaction(record, registry)
        onchain = await registry.get_image(record.sha256 or "")
        if onchain is not None:
            await _mark_registered(record, registry, tx_hash=record.blockchain_tx_hash)
            await session.commit()
            await session.refresh(record)
            return _wallet_action(record)
        if record.blockchain_tx_hash:
            outcome = await registry.verified_transaction_receipt(
                record.blockchain_tx_hash,
                expected_sender=expected.from_address,
                expected_data=expected.data,
            )
            if outcome.state == "confirmed":
                await _mark_registered(record, registry, tx_hash=outcome.tx_hash)
                await session.commit()
                await session.refresh(record)
                return _wallet_action(record)
            if outcome.state == "pending":
                record.status = ImageStatus.BLOCKCHAIN_PENDING
                await session.commit()
                await session.refresh(record)
                return _wallet_action(record)
            record.blockchain_tx_hash = None
        record.status = ImageStatus.IPFS_STORED
        record.registration_error = None
        await session.commit()
        await session.refresh(record)
        return _wallet_action(record, expected)
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{image_id}/confirm-registration", response_model=ImagePublic)
async def confirm_registration(
    image_id: UUID,
    confirmation: TransactionConfirmation,
    response: Response,
    session: SessionDep,
    media: CurrentMediaDep,
) -> ImageRecord:
    record = await owned_image_or_404(image_id, media.id, session)
    registry = get_registry(record.blockchain_contract_address)
    try:
        expected = _registration_transaction(record, registry)
        outcome = await registry.verified_transaction_receipt(
            confirmation.transaction_hash,
            expected_sender=expected.from_address,
            expected_data=expected.data,
        )
        record.blockchain_tx_hash = confirmation.transaction_hash
        if outcome.state == "pending":
            record.status = ImageStatus.BLOCKCHAIN_PENDING
            response.status_code = status.HTTP_202_ACCEPTED
        elif outcome.state == "failed":
            record.status = ImageStatus.REGISTRATION_FAILED
            record.registration_error = "La transaction MetaMask a échoué."
        else:
            await _mark_registered(record, registry, tx_hash=outcome.tx_hash)
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/{image_id}/prepare-revocation", response_model=WalletActionResponse)
async def prepare_revocation(
    image_id: UUID,
    session: SessionDep,
    media: CurrentMediaDep,
) -> WalletActionResponse:
    record = await owned_image_or_404(image_id, media.id, session)
    if record.status == ImageStatus.REVOKED:
        return _wallet_action(record)
    if record.status != ImageStatus.REGISTERED or not record.blockchain_publisher_address:
        raise HTTPException(status_code=409, detail="Cette preuve n'est pas enregistrée.")
    registry = get_registry(record.blockchain_contract_address)
    try:
        await registry.validate_configuration()
        onchain = await registry.get_image(record.sha256 or "")
        if onchain is None or not registry_matches_record(onchain, record, record.media_id):
            raise HTTPException(status_code=409, detail="La preuve on-chain diverge des données locales.")
        if Web3.to_checksum_address(onchain.publisher) != _normalize_wallet(
            record.blockchain_publisher_address
        ):
            raise HTTPException(status_code=409, detail="Le portefeuille lié n'est pas le publicateur.")
        if onchain.revoked:
            await _finish_revocation(record, get_pinata_client())
            await session.commit()
            await session.refresh(record)
            return _wallet_action(record)
        transaction = registry.revocation_transaction(
            record.sha256 or "",
            publisher_address=record.blockchain_publisher_address,
        )
        if record.revocation_tx_hash:
            outcome = await registry.verified_transaction_receipt(
                record.revocation_tx_hash,
                expected_sender=transaction.from_address,
                expected_data=transaction.data,
            )
            if outcome.state == "confirmed":
                onchain = await registry.get_image(record.sha256 or "")
                if onchain and onchain.revoked:
                    await _finish_revocation(record, get_pinata_client())
                    await session.commit()
                    await session.refresh(record)
                    return _wallet_action(record)
            elif outcome.state == "pending":
                return _wallet_action(record)
            else:
                record.revocation_tx_hash = None
        return _wallet_action(record, transaction)
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{image_id}/confirm-revocation", response_model=ImagePublic)
async def confirm_revocation(
    image_id: UUID,
    confirmation: TransactionConfirmation,
    response: Response,
    session: SessionDep,
    media: CurrentMediaDep,
) -> ImageRecord:
    record = await owned_image_or_404(image_id, media.id, session)
    if not record.blockchain_publisher_address:
        raise HTTPException(status_code=409, detail="Aucun portefeuille n'est lié à cette preuve.")
    registry = get_registry(record.blockchain_contract_address)
    transaction = registry.revocation_transaction(
        record.sha256 or "",
        publisher_address=record.blockchain_publisher_address,
    )
    try:
        outcome = await registry.verified_transaction_receipt(
            confirmation.transaction_hash,
            expected_sender=transaction.from_address,
            expected_data=transaction.data,
        )
        record.revocation_tx_hash = confirmation.transaction_hash
        if outcome.state == "pending":
            response.status_code = status.HTTP_202_ACCEPTED
        elif outcome.state == "failed":
            record.registration_error = "La transaction de révocation MetaMask a échoué."
        else:
            onchain = await registry.get_image(record.sha256 or "")
            if onchain is None or not onchain.revoked:
                raise HTTPException(status_code=409, detail="La révocation n'est pas confirmée on-chain.")
            await _finish_revocation(record, get_pinata_client())
    except HTTPException:
        raise
    except RegistryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    session: SessionDep,
    media: CurrentMediaDep,
) -> None:
    record = await owned_image_or_404(image_id, media.id, session)
    if record.status in {ImageStatus.REGISTERED, ImageStatus.REVOKED}:
        raise HTTPException(
            status_code=409,
            detail="Une preuve enregistrée doit être révoquée manuellement avec MetaMask.",
        )
    if record.status == ImageStatus.BLOCKCHAIN_PENDING:
        raise HTTPException(status_code=409, detail="La transaction blockchain est encore en attente.")
    errors = await _unpin_record(record, get_pinata_client())
    if errors:
        record.status = ImageStatus.REGISTRATION_FAILED
        record.registration_error = "; ".join(errors)
        await session.commit()
        raise HTTPException(status_code=502, detail="Le désépinglage IPFS est incomplet.")
    await session.delete(record)
    await session.commit()
