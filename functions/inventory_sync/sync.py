import logging
import os
import sys
import time
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database.session import get_session_factory
from shared.dns_provider.base import ZoneDTO
from shared.micetro.provider import MicetroProvider
from shared.models.execution import DnsSyncState
from shared.models.zones import DnsZone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("inventory_sync")

PAGE_SIZE = int(os.environ.get("SYNC_PAGE_SIZE", "200"))
# Optional cap for scoped test runs (e.g. "50") — unset/blank means sync everything.
MAX_ZONES = os.environ.get("SYNC_MAX_ZONES")


def time_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_zone(session, zone: ZoneDTO) -> int:
    stmt = (
        pg_insert(DnsZone)
        .values(
            zone_name=zone.name,
            micetro_ref=zone.ref,
            is_active=True,
            last_synced_at=time_now(),
        )
        .on_conflict_do_update(
            index_elements=["zone_name"],
            set_={"micetro_ref": zone.ref, "is_active": True, "last_synced_at": time_now()},
        )
        .returning(DnsZone.id)
    )
    return session.execute(stmt).scalar_one()


def sync_zones(session, provider: MicetroProvider) -> int:
    """Zones only — individual DNS records are never cached in Postgres, they
    are always read live from Micetro (see shared/micetro/provider.py)."""
    sync_state = DnsSyncState(sync_type="ZONES", status="RUNNING")
    session.add(sync_state)
    session.commit()

    synced_count = 0
    offset = 0
    total = None
    try:
        while total is None or offset < total:
            zones, total = provider.get_zones(offset=offset, limit=PAGE_SIZE)
            if not zones:
                break
            for zone in zones:
                upsert_zone(session, zone)
                synced_count += 1
            session.commit()
            offset += len(zones)
            logger.info("zones synced: %d/%d", offset, total)
            if MAX_ZONES and offset >= int(MAX_ZONES):
                logger.info("SYNC_MAX_ZONES=%s reached, stopping zone sync early", MAX_ZONES)
                break

        sync_state.status = "COMPLETED"
        sync_state.records_synced = synced_count
        sync_state.completed_at = time_now()
        session.commit()
    except Exception as exc:
        session.rollback()
        sync_state.status = "FAILED"
        sync_state.error_message = str(exc)[:2000]
        sync_state.completed_at = time_now()
        session.commit()
        raise

    return synced_count


def main() -> int:
    started = time.monotonic()
    provider = MicetroProvider()
    session = get_session_factory()()

    try:
        logger.info("starting zone sync (page_size=%d, max_zones=%s)", PAGE_SIZE, MAX_ZONES or "unlimited")
        synced_count = sync_zones(session, provider)
        logger.info("zone sync complete: %d zones", synced_count)
        logger.info("inventory sync finished in %.1fs", time.monotonic() - started)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
