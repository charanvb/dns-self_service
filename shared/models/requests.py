from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base
from shared.models.mixins import TimestampMixin

# Keep as plain strings (not native Postgres enums) so adding a new status later
# is a simple CHECK-constraint migration, not an ALTER TYPE.
REQUEST_STATUSES = (
    "SUBMITTED",
    "VALIDATING",
    "REJECTED",
    "VALIDATED",
    "PENDING_APPROVAL",
    "APPROVED",
    "READY_TO_EXECUTE",
    "BACKUP_IN_PROGRESS",
    "BACKUP_FAILED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "PARTIAL_FAILURE",
)

REQUEST_ITEM_ACTIONS = ("CREATE", "MODIFY", "DELETE")
REQUEST_ITEM_STATUSES = ("PENDING", "SUCCEEDED", "FAILED", "SKIPPED", "CONFLICT")


class DnsRequest(TimestampMixin, Base):
    __tablename__ = "dns_requests"
    __table_args__ = (
        CheckConstraint(f"status IN {REQUEST_STATUSES}", name="ck_dns_requests_status"),
        Index("ix_dns_requests_requestor_id", "requestor_id"),
        Index("ix_dns_requests_zone_id", "zone_id"),
        Index("ix_dns_requests_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    requestor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUBMITTED")
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    items: Mapped[list["DnsRequestItem"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class DnsRequestItem(TimestampMixin, Base):
    __tablename__ = "dns_request_items"
    __table_args__ = (
        CheckConstraint(f"action IN {REQUEST_ITEM_ACTIONS}", name="ck_dns_request_items_action"),
        CheckConstraint(f"status IN {REQUEST_ITEM_STATUSES}", name="ck_dns_request_items_status"),
        Index("ix_dns_request_items_request_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    fqdn: Mapped[str] = mapped_column(String(512), nullable=False)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Snapshot of the record at request-creation time, used to detect drift
    # (stale/conflict) against a fresh Micetro lookup right before execution.
    expected_current_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped[DnsRequest] = relationship(back_populates="items")
