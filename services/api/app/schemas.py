from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, computed_field, field_validator

from app.core.config import get_settings
from app.db.models import ImageStatus


class MediaRegister(BaseModel):
    organization_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("organization_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Le nom du média est trop court")
        return normalized


class MediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    email: EmailStr
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    media: MediaPublic


class ImageMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    author: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl | None = None
    license: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1200)

    @field_validator("title", "author", "license")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Ce champ ne peut pas être vide")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ImagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    media_id: UUID
    title: str
    author: str
    source_url: str | None
    license: str
    description: str | None
    original_filename: str
    media_type: str
    size_bytes: int
    width: int
    height: int
    status: ImageStatus
    sha256: str | None
    perceptual_hash: str | None
    difference_hash: str | None
    wavelet_hash: str | None
    fingerprint_version: int | None
    orb_descriptor_count: int | None
    ipfs_cid: str | None
    ipfs_file_id: str | None
    metadata_cid: str | None
    metadata_ipfs_file_id: str | None
    metadata_sha256: str | None
    blockchain_tx_hash: str | None
    blockchain_chain_id: int | None
    blockchain_contract_address: str | None
    blockchain_publisher_address: str | None
    blockchain_block_number: int | None
    blockchain_registered_at: datetime | None
    revocation_tx_hash: str | None
    revoked_at: datetime | None
    registration_error: str | None
    c2pa_status: str | None
    c2pa_active_manifest: str | None
    c2pa_claim_generator: str | None
    c2pa_issuer: str | None
    c2pa_validation_codes: str | None
    c2pa_asset_sha256: str | None
    c2pa_asset_size_bytes: int | None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def ipfs_url(self) -> str | None:
        base = get_settings().pinata_gateway_base_url
        return f"{base}/ipfs/{self.ipfs_cid}" if base and self.ipfs_cid else None

    @computed_field
    @property
    def metadata_url(self) -> str | None:
        base = get_settings().pinata_gateway_base_url
        return f"{base}/ipfs/{self.metadata_cid}" if base and self.metadata_cid else None

    @computed_field
    @property
    def blockchain_explorer_url(self) -> str | None:
        if not self.blockchain_tx_hash:
            return None
        base = get_settings().base_explorer_url.rstrip("/")
        return f"{base}/tx/{self.blockchain_tx_hash}"


class WalletTransactionPublic(BaseModel):
    chain_id: int
    chain_id_hex: str
    contract_address: str
    from_address: str
    data: str
    value: str = "0x0"


class WalletActionResponse(BaseModel):
    image: ImagePublic
    transaction: WalletTransactionPublic | None = None


class TransactionConfirmation(BaseModel):
    transaction_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")


class ImagePage(BaseModel):
    items: list[ImagePublic]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str | None = None


class VerificationMedia(BaseModel):
    id: UUID
    name: str
    slug: str


class VerificationImage(BaseModel):
    id: UUID
    title: str
    author: str
    source_url: str | None
    license: str
    original_filename: str
    width: int
    height: int
    created_at: datetime


class BlockchainProvenance(BaseModel):
    status: str
    chain_id: int = 84532
    contract_address: str
    transaction_hash: str | None = None
    block_number: int | None = None
    publisher_address: str | None = None
    image_cid: str | None = None
    metadata_cid: str | None = None
    image_url: str | None = None
    metadata_url: str | None = None
    explorer_url: str | None = None
    registered_at: datetime | None = None


class VerificationMatch(BaseModel):
    matched_by: str
    confidence: float = Field(ge=0, le=1)
    perceptual_distance: int | None
    difference_distance: int | None
    wavelet_distance: int | None
    good_matches: int
    inliers: int
    media: VerificationMedia
    image: VerificationImage
    registry: BlockchainProvenance


class VerificationQuery(BaseModel):
    filename: str
    size_bytes: int
    width: int
    height: int
    sha256: str


class AiDetectionResult(BaseModel):
    status: str
    provider: str = "sightengine"
    ai_generated_score: float | None = Field(default=None, ge=0, le=1)
    deepfake_score: float | None = Field(default=None, ge=0, le=1)
    likely_generator: str | None = None
    likely_generator_score: float | None = Field(default=None, ge=0, le=1)
    request_id: str | None = None
    operations: int | None = Field(default=None, ge=0)


class C2paProvenance(BaseModel):
    status: str
    active_manifest: str | None = None
    claim_generator: str | None = None
    issuer: str | None = None
    validation_codes: list[str] = Field(default_factory=list)


class VerificationResponse(BaseModel):
    query: VerificationQuery
    match_count: int
    matches: list[VerificationMatch]
    ai_detection: AiDetectionResult
    c2pa_provenance: C2paProvenance
    limitation: str
