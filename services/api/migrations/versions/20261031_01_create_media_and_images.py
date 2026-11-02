"""Create media organizations and image records.

Revision ID: 20261031_01
Revises:
Create Date: 2026-10-31
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261031_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

image_status = postgresql.ENUM(
    "draft", "registered", name="image_status", create_type=False
)


def upgrade() -> None:
    image_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "media_organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_organizations")),
        sa.UniqueConstraint("email", name=op.f("uq_media_organizations_email")),
        sa.UniqueConstraint("name", name=op.f("uq_media_organizations_name")),
        sa.UniqueConstraint("slug", name=op.f("uq_media_organizations_slug")),
    )
    op.create_table(
        "image_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("license", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=50), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("status", image_status, server_default="draft", nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("perceptual_hash", sa.String(length=64), nullable=True),
        sa.Column("ipfs_cid", sa.String(length=255), nullable=True),
        sa.Column("blockchain_tx_hash", sa.String(length=66), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_organizations.id"],
            name=op.f("fk_image_records_media_id_media_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_image_records")),
        sa.UniqueConstraint("sha256", name=op.f("uq_image_records_sha256")),
    )
    op.create_index("ix_image_records_media_created", "image_records", ["media_id", "created_at"])
    op.create_index("ix_image_records_media_id", "image_records", ["media_id"])
    op.create_index("ix_image_records_media_title", "image_records", ["media_id", "title"])


def downgrade() -> None:
    op.drop_index("ix_image_records_media_title", table_name="image_records")
    op.drop_index("ix_image_records_media_id", table_name="image_records")
    op.drop_index("ix_image_records_media_created", table_name="image_records")
    op.drop_table("image_records")
    op.drop_table("media_organizations")
    image_status.drop(op.get_bind(), checkfirst=True)
