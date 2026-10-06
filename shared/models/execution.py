from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base
from shared.models.mixins import utcnow

EXECUTION_RESULTS = ("SUCCESS", "FAILURE")


class ExecutionLog(Base):
    """One row per attempted DNS provider call for a request item (supports retries)."""

    __tablename__ = "execution_logs"
    __table_args__ = (
        CheckConstraint(f"result IN {EXECUTION_RESULTS}", name="ck_execution_logs_result"),
        Index("ix_execution_logs_request_item_id", "request_item_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_item_id: Mapped[int] = mapped_column(
        ForeignKey("dns_request_items.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="micetro")
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    """Append-only audit trail — answers who/when/what/why for every sensitive action."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("dns_requests.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DnsSyncState(Base):
    __tablename__ = "dns_sync_state"
    __table_args__ = (
        CheckConstraint("sync_type IN ('ZONES', 'RECORDS')", name="ck_dns_sync_state_sync_type"),
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')", name="ck_dns_sync_state_status"
        ),
        Index("ix_dns_sync_state_zone_id", "zone_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_synced: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DnsZoneBackup(Base):
    """Tracks the Azure Automation runbook backup that the Executor requires to
    succeed before any CREATE/MODIFY/DELETE is applied to a zone."""

    __tablename__ = "dns_zone_backups"
    __table_args__ = (
        CheckConstraint(
            "status IN ('TRIGGERED', 'COMPLETED', 'FAILED', 'TIMEOUT')",
            name="ck_dns_zone_backups_status",
        ),
        Index("ix_dns_zone_backups_request_id", "request_id"),
        Index("ix_dns_zone_backups_zone_id", "zone_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    azure_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="TRIGGERED")
    backup_location: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
