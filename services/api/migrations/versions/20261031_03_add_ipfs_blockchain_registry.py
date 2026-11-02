"""Add IPFS and Base Sepolia registry lifecycle.

Revision ID: 20261031_03
Revises: 20261031_02
Create Date: 2026-10-31
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261031_03"
down_revision: str | None = "20261031_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_STATUSES = (
    "ipfs_stored",
    "blockchain_pending",
    "registration_failed",
    "revoked",
)


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            for value in NEW_STATUSES:
                op.execute(f"ALTER TYPE image_status ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("image_records", sa.Column("ipfs_file_id", sa.String(length=64)))
    op.add_column("image_records", sa.Column("metadata_cid", sa.String(length=255)))
    op.add_column("image_records", sa.Column("metadata_ipfs_file_id", sa.String(length=64)))
    op.add_column("image_records", sa.Column("metadata_sha256", sa.String(length=64)))
    op.add_column("image_records", sa.Column("blockchain_chain_id", sa.Integer()))
    op.add_column("image_records", sa.Column("blockchain_contract_address", sa.String(length=42)))
    op.add_column("image_records", sa.Column("blockchain_publisher_address", sa.String(length=42)))
    op.add_column("image_records", sa.Column("blockchain_block_number", sa.BigInteger()))
    op.add_column("image_records", sa.Column("blockchain_registered_at", sa.DateTime(timezone=True)))
    op.add_column("image_records", sa.Column("revocation_tx_hash", sa.String(length=66)))
    op.add_column("image_records", sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.add_column("image_records", sa.Column("registration_error", sa.Text()))


def downgrade() -> None:
    op.drop_column("image_records", "registration_error")
    op.drop_column("image_records", "revoked_at")
    op.drop_column("image_records", "revocation_tx_hash")
    op.drop_column("image_records", "blockchain_registered_at")
    op.drop_column("image_records", "blockchain_block_number")
    op.drop_column("image_records", "blockchain_publisher_address")
    op.drop_column("image_records", "blockchain_contract_address")
    op.drop_column("image_records", "blockchain_chain_id")
    op.drop_column("image_records", "metadata_sha256")
    op.drop_column("image_records", "metadata_ipfs_file_id")
    op.drop_column("image_records", "metadata_cid")
    op.drop_column("image_records", "ipfs_file_id")
    # PostgreSQL enum values are intentionally retained on downgrade.
