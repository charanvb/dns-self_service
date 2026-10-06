"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-07

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.BigInteger, sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "dns_zones",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("zone_name", sa.String(255), nullable=False, unique=True),
        sa.Column("micetro_ref", sa.String(255), nullable=False),
        sa.Column("requires_approval", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_dns_zones_zone_name_trgm", "dns_zones", ["zone_name"])

    op.create_table(
        "zone_admins",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("zone_id", "user_id", name="uq_zone_admins_zone_user"),
    )

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
    )
    op.create_index("ix_dns_records_zone_id", "dns_records", ["zone_id"])
    op.create_index("ix_dns_records_fqdn", "dns_records", ["fqdn"])
    op.create_index("ix_dns_records_record_type", "dns_records", ["record_type"])

    request_status = (
        "SUBMITTED", "VALIDATING", "REJECTED", "VALIDATED", "PENDING_APPROVAL", "APPROVED",
        "READY_TO_EXECUTE", "BACKUP_IN_PROGRESS", "BACKUP_FAILED", "PROCESSING", "COMPLETED",
        "FAILED", "PARTIAL_FAILURE",
    )
    op.create_table(
        "dns_requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("requestor_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUBMITTED"),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(f"status IN {request_status}", name="ck_dns_requests_status"),
    )
    op.create_index("ix_dns_requests_requestor_id", "dns_requests", ["requestor_id"])
    op.create_index("ix_dns_requests_zone_id", "dns_requests", ["zone_id"])
    op.create_index("ix_dns_requests_status", "dns_requests", ["status"])

    op.create_table(
        "dns_request_items",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "request_id", sa.BigInteger, sa.ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("record_type", sa.String(20), nullable=False),
        sa.Column("fqdn", sa.String(512), nullable=False),
        sa.Column("ttl", sa.Integer, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("expected_current_value", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('CREATE', 'MODIFY', 'DELETE')", name="ck_dns_request_items_action"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'SKIPPED', 'CONFLICT')",
            name="ck_dns_request_items_status",
        ),
    )
    op.create_index("ix_dns_request_items_request_id", "dns_request_items", ["request_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "request_id", sa.BigInteger, sa.ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')", name="ck_approval_requests_status"
        ),
    )
    op.create_index("ix_approval_requests_request_id", "approval_requests", ["request_id"])
    op.create_index("ix_approval_requests_zone_id", "approval_requests", ["zone_id"])

    op.create_table(
        "approval_actions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "approval_request_id",
            sa.BigInteger,
            sa.ForeignKey("approval_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("approver_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('APPROVE', 'REJECT')", name="ck_approval_actions_action"),
    )

    op.create_table(
        "dns_policies",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "policy_rules",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "policy_id", sa.BigInteger, sa.ForeignKey("dns_policies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_policy_rules_policy_id", "policy_rules", ["policy_id"])

    op.create_table(
        "execution_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "request_item_id",
            sa.BigInteger,
            sa.ForeignKey("dns_request_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False, server_default="micetro"),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("response_payload", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("result IN ('SUCCESS', 'FAILURE')", name="ck_execution_logs_result"),
    )
    op.create_index("ix_execution_logs_request_item_id", "execution_logs", ["request_item_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "request_id", sa.BigInteger, sa.ForeignKey("dns_requests.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("extra", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    op.create_table(
        "dns_sync_state",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("sync_type", sa.String(20), nullable=False),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_synced", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sync_type IN ('ZONES', 'RECORDS')", name="ck_dns_sync_state_sync_type"),
        sa.CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_dns_sync_state_status"),
    )
    op.create_index("ix_dns_sync_state_zone_id", "dns_sync_state", ["zone_id"])

    op.create_table(
        "dns_zone_backups",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "request_id", sa.BigInteger, sa.ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("zone_id", sa.BigInteger, sa.ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("azure_job_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="TRIGGERED"),
        sa.Column("backup_location", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('TRIGGERED', 'COMPLETED', 'FAILED', 'TIMEOUT')", name="ck_dns_zone_backups_status"
        ),
    )
    op.create_index("ix_dns_zone_backups_request_id", "dns_zone_backups", ["request_id"])
    op.create_index("ix_dns_zone_backups_zone_id", "dns_zone_backups", ["zone_id"])

    op.create_table(
        "system_config",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Seed fixed application roles.
    roles_table = sa.table("roles", sa.column("name", sa.String), sa.column("description", sa.String))
    op.bulk_insert(
        roles_table,
        [
            {"name": "REQUESTOR", "description": "Can search zones/records and create DNS requests"},
            {"name": "ZONE_ADMIN", "description": "Requestor + approves requests for assigned zones"},
            {"name": "CLOUDOPS_ADMIN", "description": "Full administrative access"},
        ],
    )


def downgrade() -> None:
    op.drop_table("system_config")
    op.drop_table("dns_zone_backups")
    op.drop_table("dns_sync_state")
    op.drop_table("audit_logs")
    op.drop_table("execution_logs")
    op.drop_table("policy_rules")
    op.drop_table("dns_policies")
    op.drop_table("approval_actions")
    op.drop_table("approval_requests")
    op.drop_table("dns_request_items")
    op.drop_table("dns_requests")
    op.drop_table("dns_records")
    op.drop_table("zone_admins")
    op.drop_table("dns_zones")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
