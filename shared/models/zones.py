from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
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

# Individual DNS records are never cached in Postgres — they must always be
# read live from Micetro (see shared/micetro/provider.py), so there is no
# DnsRecord model/table here.
