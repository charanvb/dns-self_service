from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.auth.fastapi_deps import get_current_user
from shared.database.session import get_session
from shared.micetro.provider import MicetroProvider
from shared.models.zones import DnsRecord, DnsZone

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("")
def search_zones(
    search: str = Query("", min_length=0, max_length=255),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    query = select(DnsZone).where(DnsZone.is_active.is_(True))
    if search:
        query = query.where(DnsZone.zone_name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(DnsZone.zone_name).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [{"id": z.id, "zone_name": z.zone_name, "requires_approval": z.requires_approval} for z in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{zone_id}/records")
def search_zone_records(
    zone_id: int,
    search: str = Query("", min_length=0, max_length=255),
    record_type: str | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    db: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    zone = db.get(DnsZone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")

    query = select(DnsRecord).where(DnsRecord.zone_id == zone_id)
    if search:
        query = query.where(DnsRecord.fqdn.ilike(f"%{search}%"))
    if record_type:
        query = query.where(DnsRecord.record_type == record_type)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(DnsRecord.fqdn).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "fqdn": r.fqdn,
                "record_type": r.record_type,
                "ttl": r.ttl,
                "value": r.value,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{zone_id}/live-records")
def live_zone_records(
    zone_id: int,
    db: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    """Fetches every record in the zone directly from Micetro (bypasses the
    Postgres inventory cache entirely) — used by the request wizard, which
    must act on authoritative, not-possibly-stale data. Deliberately slower
    than the cached /records endpoint; that's an accepted tradeoff here."""
    zone = db.get(DnsZone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")

    provider = MicetroProvider()
    records = provider.list_all_records(zone.micetro_ref, zone_name=zone.zone_name)
    return {
        "items": [
            {"ref": r.ref, "fqdn": r.name, "record_type": r.record_type, "ttl": r.ttl, "value": r.data}
            for r in records
        ],
        "total": len(records),
    }
