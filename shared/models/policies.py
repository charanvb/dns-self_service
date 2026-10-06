from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base
from shared.models.mixins import TimestampMixin


class DnsPolicy(TimestampMixin, Base):
    __tablename__ = "dns_policies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rules: Mapped[list["PolicyRule"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class PolicyRule(TimestampMixin, Base):
    """A single evaluable condition within a policy (e.g. SPF-duplicate check,
    restricted record type, zone-admin-approval-required). `config` holds the
    rule-specific parameters so new rule types don't require schema changes.
    """

    __tablename__ = "policy_rules"
    __table_args__ = (Index("ix_policy_rules_policy_id", "policy_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("dns_policies.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    policy: Mapped[DnsPolicy] = relationship(back_populates="rules")
