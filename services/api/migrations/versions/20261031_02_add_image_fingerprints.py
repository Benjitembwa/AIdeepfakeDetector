"""Add perceptual and local image fingerprints.

Revision ID: 20261031_02
Revises: 20261031_01
Create Date: 2026-10-31
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261031_02"
down_revision: str | None = "20261031_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE image_status ADD VALUE IF NOT EXISTS 'fingerprinted'")

    op.add_column("image_records", sa.Column("difference_hash", sa.String(length=64)))
    op.add_column("image_records", sa.Column("wavelet_hash", sa.String(length=64)))
    op.add_column("image_records", sa.Column("fingerprint_version", sa.Integer()))
    op.add_column("image_records", sa.Column("orb_keypoints", sa.LargeBinary()))
    op.add_column("image_records", sa.Column("orb_descriptors", sa.LargeBinary()))
    op.add_column("image_records", sa.Column("orb_descriptor_count", sa.Integer()))
    op.drop_constraint("uq_image_records_sha256", "image_records", type_="unique")
    op.create_index("ix_image_records_sha256", "image_records", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_image_records_sha256", table_name="image_records")
    op.create_unique_constraint("uq_image_records_sha256", "image_records", ["sha256"])
    op.drop_column("image_records", "orb_descriptor_count")
    op.drop_column("image_records", "orb_descriptors")
    op.drop_column("image_records", "orb_keypoints")
    op.drop_column("image_records", "fingerprint_version")
    op.drop_column("image_records", "wavelet_hash")
    op.drop_column("image_records", "difference_hash")

    # PostgreSQL ne sait pas retirer simplement une valeur d'un enum. La valeur
    # `fingerprinted` reste donc disponible après un downgrade sans toucher aux données.
