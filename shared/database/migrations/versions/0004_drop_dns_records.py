"""Drop dns_records (records are never cached, always read live from Micetro)

Revision ID: 0004_drop_dns_records
Revises: 0003_dns_records_uniq
Create Date: 2026-10-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0004_drop_dns_records"
down_revision = "0003_dns_records_uniq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("dns_records")


def downgrade() -> None:
    op.create_table(
        "dns_records",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("micetro_ref", sa.String(255), nullable=False),
        sa.Column("fqdn", sa.String(512), nullable=False),
        sa.Column("record_type", sa.String(20), nullable=False),
        sa.Column("ttl", sa.Integer, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("zone_id", "micetro_ref", name="uq_dns_records_zone_micetro_ref"),
    )
    op.create_index("ix_dns_records_zone_id", "dns_records", ["zone_id"])
    op.create_index("ix_dns_records_fqdn", "dns_records", ["fqdn"])
    op.create_index("ix_dns_records_record_type", "dns_records", ["record_type"])
