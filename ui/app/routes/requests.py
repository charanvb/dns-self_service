from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auth.fastapi_deps import CurrentUser, get_current_user
from shared.database.session import get_session
from shared.models.requests import DnsRequest, DnsRequestItem
from shared.models.zones import DnsRecord, DnsZone
from shared.validation.common import ValidationError, validate_fqdn, validate_ttl
from shared.validation.registry import SUPPORTED_RECORD_TYPES, validate_record_value

from ui.app.schemas_requests import CreateRequestIn, RequestItemOut, RequestOut

router = APIRouter(prefix="/api/requests", tags=["requests"])

DEFAULT_TTL = 300


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    body: CreateRequestIn,
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    zone = db.get(DnsZone, body.zone_id)
    if zone is None or not zone.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")

    request_row = DnsRequest(requestor_id=user.user_id, zone_id=zone.id, status="SUBMITTED",
                              justification=body.justification)
    db.add(request_row)
    db.flush()  # assign request_row.id without committing yet

    item_rows: list[DnsRequestItem] = []
    try:
        for item in body.items:
            if item.record_type not in SUPPORTED_RECORD_TYPES:
                raise ValidationError("record_type", f"Unsupported record type: {item.record_type}")

            validate_fqdn(item.fqdn, zone.zone_name)
            ttl = validate_ttl(item.ttl if item.ttl is not None else DEFAULT_TTL)

            expected_current_value = None
            new_value = None

            if item.action == "CREATE":
                new_value = validate_record_value(item.record_type, item.value)
            else:
                # MODIFY / DELETE must reference a record we actually have in
                # inventory — a fresh Micetro lookup happens later at execution
                # time (Phase 9); this snapshot is only for the drift check.
                if item.source_record_id is None:
                    raise ValidationError("source_record_id", "Select an existing record to modify/delete")
                source = db.get(DnsRecord, item.source_record_id)
                if source is None or source.zone_id != zone.id:
                    raise ValidationError("source_record_id", "Selected record not found in this zone")
                expected_current_value = {
                    "record_type": source.record_type,
                    "ttl": source.ttl,
                    "value": source.value,
                }
                if item.action == "MODIFY":
                    new_value = validate_record_value(item.record_type, item.value)

            item_rows.append(
                DnsRequestItem(
                    request_id=request_row.id,
                    action=item.action,
                    record_type=item.record_type,
                    fqdn=item.fqdn.rstrip("."),
                    ttl=ttl,
                    new_value=new_value,
                    expected_current_value=expected_current_value,
                    status="PENDING",
                )
            )
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"field": exc.field, "message": exc.message})

    db.add_all(item_rows)
    db.commit()
    db.refresh(request_row)
    for row in item_rows:
        db.refresh(row)

    return RequestOut(
        id=request_row.id,
        zone_id=request_row.zone_id,
        status=request_row.status,
        justification=request_row.justification,
        items=[RequestItemOut.from_model(r) for r in item_rows],
    )


@router.get("")
def list_my_requests(
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    rows = db.execute(
        select(DnsRequest, DnsZone.zone_name)
        .join(DnsZone, DnsZone.id == DnsRequest.zone_id)
        .where(DnsRequest.requestor_id == user.user_id)
        .order_by(DnsRequest.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "zone_name": zone_name,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r, zone_name in rows
    ]


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    request_row = db.get(DnsRequest, request_id)
    if request_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if request_row.requestor_id != user.user_id and not user.has_role("CLOUDOPS_ADMIN"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your request")

    return RequestOut(
        id=request_row.id,
        zone_id=request_row.zone_id,
        status=request_row.status,
        justification=request_row.justification,
        items=[RequestItemOut.from_model(r) for r in request_row.items],
    )
