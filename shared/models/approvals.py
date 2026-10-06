from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base
from shared.models.mixins import TimestampMixin, utcnow

APPROVAL_REQUEST_STATUSES = ("PENDING", "APPROVED", "REJECTED", "CANCELLED")
APPROVAL_ACTION_TYPES = ("APPROVE", "REJECT")


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(f"status IN {APPROVAL_REQUEST_STATUSES}", name="ck_approval_requests_status"),
        Index("ix_approval_requests_request_id", "request_id"),
        Index("ix_approval_requests_zone_id", "zone_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("dns_requests.id", ondelete="CASCADE"), nullable=False)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="approval_request", cascade="all, delete-orphan"
    )


class ApprovalAction(Base):
    __tablename__ = "approval_actions"
    __table_args__ = (CheckConstraint(f"action IN {APPROVAL_ACTION_TYPES}", name="ck_approval_actions_action"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="actions")
