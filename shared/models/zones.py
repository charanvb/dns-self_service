from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.base import Base
from shared.models.mixins import TimestampMixin


class DnsZone(TimestampMixin, Base):
    """Inventory cache of Micetro zones — NOT authoritative, refreshed by sync job."""

    __tablename__ = "dns_zones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    zone_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    micetro_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_dns_zones_zone_name_trgm", "zone_name"),)


class ZoneAdmin(Base):
    __tablename__ = "zone_admins"
    __table_args__ = (UniqueConstraint("zone_id", "user_id", name="uq_zone_admins_zone_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    zone: Mapped[DnsZone] = relationship()


class DnsRecord(TimestampMixin, Base):
    """Inventory cache of Micetro records — NOT authoritative, refreshed by sync job.

    Always re-fetched from Micetro before MODIFY/DELETE execution; never used to
    decide the outcome of a DNS change by itself.
    """

    __tablename__ = "dns_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("dns_zones.id", ondelete="CASCADE"), nullable=False)
    micetro_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    fqdn: Mapped[str] = mapped_column(String(512), nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_dns_records_zone_id", "zone_id"),
        Index("ix_dns_records_fqdn", "fqdn"),
        Index("ix_dns_records_record_type", "record_type"),
    )
