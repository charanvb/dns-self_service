"""Seed a default DNS policy (restricted record types, empty by default)

Revision ID: 0006_seed_default_policy
Revises: 0005_seed_rate_limit
Create Date: 2026-10-07

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_seed_default_policy"
down_revision = "0005_seed_rate_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    policies = sa.table(
        "dns_policies", sa.column("id", sa.BigInteger), sa.column("name", sa.String),
        sa.column("description", sa.String), sa.column("is_active", sa.Boolean),
    )
    result = conn.execute(
        sa.insert(policies)
        .values(
            name="Default DNS Policy",
            description="Baseline policy evaluated for every request. Zone-level approval is "
            "controlled by dns_zones.requires_approval; record-type restrictions are configured "
            "via this policy's rules.",
            is_active=True,
        )
        .returning(policies.c.id)
    )
    policy_id = result.scalar_one()

    policy_rules = sa.table(
        "policy_rules", sa.column("policy_id", sa.BigInteger), sa.column("rule_type", sa.String),
        sa.column("config", postgresql.JSONB), sa.column("is_active", sa.Boolean),
    )
    conn.execute(
        sa.insert(policy_rules).values(
            policy_id=policy_id,
            rule_type="restricted_record_type",
            # Empty by default — CLOUDOPS_ADMIN can populate record_types
            # (e.g. ["MX"]) and action ("REJECT" or "REQUIRE_APPROVAL") later.
            config={"record_types": [], "action": "REQUIRE_APPROVAL"},
            is_active=True,
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM dns_policies WHERE name = 'Default DNS Policy'")
