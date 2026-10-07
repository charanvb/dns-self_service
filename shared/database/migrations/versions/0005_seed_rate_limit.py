"""Seed system_config with the requestor rate limit default

Revision ID: 0005_seed_rate_limit
Revises: 0004_drop_dns_records
Create Date: 2026-10-07

"""
import sqlalchemy as sa
from alembic import op

revision = "0005_seed_rate_limit"
down_revision = "0004_drop_dns_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    system_config = sa.table(
        "system_config", sa.column("key", sa.String), sa.column("value", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        system_config,
        [
            {
                "key": "requestor_rate_limit_per_24h",
                "value": "2",
                "description": (
                    "Max DNS requests a REQUESTOR (not ZONE_ADMIN/CLOUDOPS_ADMIN) may submit per "
                    "rolling 24h window. Counted per request, not per record item."
                ),
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_config WHERE key = 'requestor_rate_limit_per_24h'")
