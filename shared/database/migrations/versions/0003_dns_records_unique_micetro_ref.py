"""Add unique constraint for upsert-safe record sync

Revision ID: 0003_dns_records_unique_micetro_ref
Revises: 0002_add_local_test_users
Create Date: 2026-10-07

"""
from alembic import op

revision = "0003_dns_records_unique_micetro_ref"
down_revision = "0002_add_local_test_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_dns_records_zone_micetro_ref", "dns_records", ["zone_id", "micetro_ref"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_dns_records_zone_micetro_ref", "dns_records", type_="unique")
