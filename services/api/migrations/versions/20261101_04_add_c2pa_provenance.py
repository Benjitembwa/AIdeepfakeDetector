"""Add C2PA provenance fields.

Revision ID: 20261101_04
Revises: 20261031_03
Create Date: 2026-11-01
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261101_04"
down_revision: str | None = "20261031_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("image_records", sa.Column("c2pa_status", sa.String(length=32)))
    op.add_column("image_records", sa.Column("c2pa_active_manifest", sa.String(length=255)))
    op.add_column("image_records", sa.Column("c2pa_claim_generator", sa.String(length=255)))
    op.add_column("image_records", sa.Column("c2pa_issuer", sa.String(length=255)))
    op.add_column("image_records", sa.Column("c2pa_validation_codes", sa.Text()))
    op.add_column("image_records", sa.Column("c2pa_manifest", sa.Text()))
    op.add_column("image_records", sa.Column("c2pa_asset_sha256", sa.String(length=64)))
    op.add_column("image_records", sa.Column("c2pa_asset_size_bytes", sa.BigInteger()))


def downgrade() -> None:
    op.drop_column("image_records", "c2pa_asset_size_bytes")
    op.drop_column("image_records", "c2pa_asset_sha256")
    op.drop_column("image_records", "c2pa_manifest")
    op.drop_column("image_records", "c2pa_validation_codes")
    op.drop_column("image_records", "c2pa_issuer")
    op.drop_column("image_records", "c2pa_claim_generator")
    op.drop_column("image_records", "c2pa_active_manifest")
    op.drop_column("image_records", "c2pa_status")
