import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, LargeBinary, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ImageStatus(str, enum.Enum):
    DRAFT = "draft"
    FINGERPRINTED = "fingerprinted"
    IPFS_STORED = "ipfs_stored"
    BLOCKCHAIN_PENDING = "blockchain_pending"
    REGISTRATION_FAILED = "registration_failed"
    REGISTERED = "registered"
    REVOKED = "revoked"


class MediaOrganization(TimestampMixin, Base):
    __tablename__ = "media_organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    images: Mapped[list["ImageRecord"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class ImageRecord(TimestampMixin, Base):
    __tablename__ = "image_records"
    __table_args__ = (
        Index("ix_image_records_media_created", "media_id", "created_at"),
        Index("ix_image_records_media_title", "media_id", "title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    license: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[ImageStatus] = mapped_column(
        Enum(
            ImageStatus,
            name="image_status",
            native_enum=True,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
        default=ImageStatus.DRAFT,
        server_default=ImageStatus.DRAFT.value,
    )
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(64))
    difference_hash: Mapped[str | None] = mapped_column(String(64))
    wavelet_hash: Mapped[str | None] = mapped_column(String(64))
    fingerprint_version: Mapped[int | None] = mapped_column()
    orb_keypoints: Mapped[bytes | None] = mapped_column(LargeBinary)
    orb_descriptors: Mapped[bytes | None] = mapped_column(LargeBinary)
    orb_descriptor_count: Mapped[int | None] = mapped_column()
    ipfs_cid: Mapped[str | None] = mapped_column(String(255))
    ipfs_file_id: Mapped[str | None] = mapped_column(String(64))
    metadata_cid: Mapped[str | None] = mapped_column(String(255))
    metadata_ipfs_file_id: Mapped[str | None] = mapped_column(String(64))
    metadata_sha256: Mapped[str | None] = mapped_column(String(64))
    blockchain_tx_hash: Mapped[str | None] = mapped_column(String(66))
    blockchain_chain_id: Mapped[int | None] = mapped_column()
    blockchain_contract_address: Mapped[str | None] = mapped_column(String(42))
    blockchain_publisher_address: Mapped[str | None] = mapped_column(String(42))
    blockchain_block_number: Mapped[int | None] = mapped_column(BigInteger)
    blockchain_registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_tx_hash: Mapped[str | None] = mapped_column(String(66))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_error: Mapped[str | None] = mapped_column(Text)
    c2pa_status: Mapped[str | None] = mapped_column(String(32))
    c2pa_active_manifest: Mapped[str | None] = mapped_column(String(255))
    c2pa_claim_generator: Mapped[str | None] = mapped_column(String(255))
    c2pa_issuer: Mapped[str | None] = mapped_column(String(255))
    c2pa_validation_codes: Mapped[str | None] = mapped_column(Text)
    c2pa_manifest: Mapped[str | None] = mapped_column(Text)
    c2pa_asset_sha256: Mapped[str | None] = mapped_column(String(64))
    c2pa_asset_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    media: Mapped[MediaOrganization] = relationship(back_populates="images")
