import logging
import os
import sys
import time

from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database.session import get_session_factory
from shared.dns_provider.base import RecordDTO, ZoneDTO
from shared.micetro.provider import MicetroProvider
from shared.models.execution import DnsSyncState
from shared.models.zones import DnsRecord, DnsZone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("inventory_sync")

PAGE_SIZE = int(os.environ.get("SYNC_PAGE_SIZE", "200"))
# Optional cap for scoped test runs (e.g. "50") — unset/blank means sync everything.
MAX_ZONES = os.environ.get("SYNC_MAX_ZONES")
SYNC_RECORDS = os.environ.get("SYNC_RECORDS", "true").lower() != "false"


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


def upsert_record(session, zone_id: int, record: RecordDTO) -> None:
    ttl_int = None
    try:
        ttl_int = int(record.ttl)
    except (TypeError, ValueError):
        ttl_int = 0

    stmt = (
        pg_insert(DnsRecord)
        .values(
            zone_id=zone_id,
            micetro_ref=record.ref,
            fqdn=record.name,
            record_type=record.record_type,
            ttl=ttl_int,
            value=record.data,
            last_synced_at=time_now(),
        )
        .on_conflict_do_update(
            index_elements=["zone_id", "micetro_ref"],
            set_={
                "fqdn": record.name,
                "record_type": record.record_type,
                "ttl": ttl_int,
                "value": record.data,
                "last_synced_at": time_now(),
            },
        )
    )
    session.execute(stmt)


def time_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def sync_zones(session, provider: MicetroProvider) -> list[tuple[int, str]]:
    sync_state = DnsSyncState(sync_type="ZONES", status="RUNNING")
    session.add(sync_state)
    session.commit()

    synced: list[tuple[int, str]] = []
    offset = 0
    total = None
    try:
        while total is None or offset < total:
            zones, total = provider.get_zones(offset=offset, limit=PAGE_SIZE)
            if not zones:
                break
            for zone in zones:
                zone_id = upsert_zone(session, zone)
                synced.append((zone_id, zone.ref))
            session.commit()
            offset += len(zones)
            logger.info("zones synced: %d/%d", offset, total)
            if MAX_ZONES and offset >= int(MAX_ZONES):
                logger.info("SYNC_MAX_ZONES=%s reached, stopping zone sync early", MAX_ZONES)
                break

        sync_state.status = "COMPLETED"
        sync_state.records_synced = len(synced)
        sync_state.completed_at = time_now()
        session.commit()
    except Exception as exc:
        session.rollback()
        sync_state.status = "FAILED"
        sync_state.error_message = str(exc)[:2000]
        sync_state.completed_at = time_now()
        session.commit()
        raise

    return synced


def sync_records_for_zone(session, provider: MicetroProvider, zone_id: int, zone_ref: str) -> int:
    sync_state = DnsSyncState(sync_type="RECORDS", zone_id=zone_id, status="RUNNING")
    session.add(sync_state)
    session.commit()

    count = 0
    offset = 0
    total = None
    try:
        while total is None or offset < total:
            records, total = provider.search_records(zone_ref=zone_ref, offset=offset, limit=PAGE_SIZE)
            if not records:
                break
            for record in records:
                upsert_record(session, zone_id, record)
            session.commit()
            offset += len(records)
            count += len(records)

        sync_state.status = "COMPLETED"
        sync_state.records_synced = count
        sync_state.completed_at = time_now()
        session.commit()
    except Exception as exc:
        session.rollback()
        sync_state.status = "FAILED"
        sync_state.error_message = str(exc)[:2000]
        sync_state.completed_at = time_now()
        session.commit()
        logger.error("record sync failed for zone_id=%s: %s", zone_id, exc)
        return count

    return count


def main() -> int:
    started = time.monotonic()
    provider = MicetroProvider()
    session = get_session_factory()()

    try:
        logger.info("starting zone sync (page_size=%d, max_zones=%s)", PAGE_SIZE, MAX_ZONES or "unlimited")
        synced_zones = sync_zones(session, provider)
        logger.info("zone sync complete: %d zones", len(synced_zones))

        if SYNC_RECORDS:
            total_records = 0
            for i, (zone_id, zone_ref) in enumerate(synced_zones, start=1):
                n = sync_records_for_zone(session, provider, zone_id, zone_ref)
                total_records += n
                logger.info("[%d/%d] zone_id=%s synced %d records", i, len(synced_zones), zone_id, n)
            logger.info("record sync complete: %d records across %d zones", total_records, len(synced_zones))
        else:
            logger.info("SYNC_RECORDS=false — skipping record sync")

        logger.info("inventory sync finished in %.1fs", time.monotonic() - started)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
