from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auth.fastapi_deps import CurrentUser, get_current_user
from shared.database.session import get_session
from shared.executor.engine import trigger_execution
from shared.micetro.provider import MicetroProvider
from shared.models.approvals import ApprovalRequest
from shared.models.requests import DnsRequest, DnsRequestItem
from shared.models.zones import DnsZone, ZoneAdmin
from shared.policy.engine import PolicyEngine
from shared.policy.rate_limit import RateLimitExceeded, check_request_rate_limit
from shared.validation.common import ValidationError, validate_fqdn, validate_ttl
from shared.validation.registry import SUPPORTED_RECORD_TYPES, validate_record_value

from ui.app.schemas import CreateRequestIn, RequestItemOut, RequestOut

import logging

logger = logging.getLogger("requests_api")

router = APIRouter(prefix="/api/requests", tags=["requests"])

DEFAULT_TTL = 300


def _is_spf_value(text: str) -> bool:
    return text.strip().lower().startswith("v=spf1")


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    body: CreateRequestIn,
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
):
    zone = db.get(DnsZone, body.zone_id)
    if zone is None or not zone.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")

    try:
        check_request_rate_limit(db, user.user_id, user.roles)
    except RateLimitExceeded as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc))

    request_row = DnsRequest(requestor_id=user.user_id, zone_id=zone.id, status="SUBMITTED",
                              justification=body.justification)
    db.add(request_row)
    db.flush()  # assign request_row.id without committing yet

    provider = MicetroProvider()
    # Cached per (fqdn, record_type) lookup to avoid redundant Micetro calls
    # while validating items within the same request.
    targeted_records_cache: dict[tuple[str, str | None], list] = {}

    def get_records_for_name(fqdn_name: str, record_type: str | None = None):
        cache_key = (fqdn_name, record_type)
        if cache_key not in targeted_records_cache:
            targeted_records_cache[cache_key] = provider.find_records_by_name(
                zone.micetro_ref, fqdn=fqdn_name, record_type=record_type, zone_name=zone.zone_name
            )
        return targeted_records_cache[cache_key]

    item_rows: list[DnsRequestItem] = []
    # Tracks (fqdn, record_type) pairs already queued for CREATE earlier in
    # THIS SAME request — the live-Micetro duplicate check below only catches
    # records that already exist in Micetro, not two new items in one request
    # both trying to create the same name+type.
    create_keys_seen: set[tuple[str, str]] = set()
    try:
        for item in body.items:
            if item.record_type not in SUPPORTED_RECORD_TYPES:
                raise ValidationError("record_type", f"Unsupported record type: {item.record_type}")

            # "@" is the conventional DNS zone-file alias for the apex — treat
            # it exactly as if the user left the label blank, not as a literal
            # (invalid) label.
            fqdn_raw = item.fqdn.strip()
            if fqdn_raw.split(".")[0] == "@":
                fqdn_raw = zone.zone_name

            validate_fqdn(fqdn_raw, zone.zone_name, record_type=item.record_type)
            ttl = validate_ttl(item.ttl if item.ttl is not None else DEFAULT_TTL)

            # Zone apex holds critical NS/SOA/root records — block self-service
            # changes there for every action EXCEPT TXT (SPF/DMARC/domain-
            # verification records legitimately live at the apex).
            fqdn_clean = fqdn_raw.rstrip(".").lower()
            is_apex = fqdn_clean == zone.zone_name.rstrip(".").lower()
            if is_apex and item.record_type != "TXT":
                raise ValidationError(
                    "fqdn",
                    "Changes to the zone apex record are not allowed via self-service "
                    "(TXT records are the only exception). Contact your DNS/CloudOps team directly.",
                )

            expected_current_value = None
            new_value = None

            if item.action == "CREATE":
                new_value = validate_record_value(item.record_type, item.value)

                create_key = (fqdn_clean, item.record_type)
                if create_key in create_keys_seen:
                    raise ValidationError(
                        "fqdn",
                        f"This request already has another CREATE for a {item.record_type} record at "
                        f"'{fqdn_raw}'. Combine them into one change.",
                    )

                records = get_records_for_name(fqdn_clean, item.record_type)
                logger.info(
                    "duplicate-check zone=%s fqdn_clean=%r type=%s live_record_count=%d sample=%r",
                    zone.zone_name, fqdn_clean, item.record_type, len(records),
                    [(r.name, r.record_type) for r in records[:10]],
                )
                duplicate = next(
                    (
                        r for r in records
                        if r.name.rstrip(".").lower() == fqdn_clean and r.record_type == item.record_type
                    ),
                    None,
                )
                logger.info("duplicate-check result=%s", "FOUND:" + duplicate.ref if duplicate else "none")
                if duplicate is not None:
                    raise ValidationError(
                        "fqdn",
                        f"A {item.record_type} record already exists for '{fqdn_raw}' in Micetro. "
                        "Use a Modify request instead of Create.",
                    )
                create_keys_seen.add(create_key)

                # SPF-specific rule (independent of the exact type+name duplicate
                # check above): only one SPF record is allowed per name, even if
                # its exact text differs from the one being created.
                if item.record_type == "TXT" and _is_spf_value(new_value.get("text", "")):
                    txt_records = get_records_for_name(fqdn_clean, "TXT")
                    spf_exists = any(
                        r.name.rstrip(".").lower() == fqdn_clean
                        and r.record_type in ("TXT", "SPF")
                        and _is_spf_value(r.data)
                        for r in txt_records
                    )
                    if spf_exists:
                        raise ValidationError(
                            "value",
                            f"An SPF record already exists for '{fqdn_raw}'. Only one SPF record is "
                            "allowed per name — use a Modify request to change it instead.",
                        )
            else:
                # MODIFY / DELETE must reference a live Micetro record, fetched
                # fresh here (not the Postgres cache) to avoid any discrepancy.
                if not item.source_record_ref:
                    raise ValidationError("source_record_ref", "Select an existing record to modify/delete")
                try:
                    source = provider.get_record(item.source_record_ref, zone_name=zone.zone_name)
                except Exception:
                    raise ValidationError(
                        "source_record_ref",
                        "Could not find that record in Micetro — it may have changed. Please refresh and retry.",
                    )
                expected_current_value = {
                    "ref": source.ref,
                    "record_type": source.record_type,
                    "ttl": source.ttl,
                    "value": source.data,
                }
                if item.action == "MODIFY":
                    new_value = validate_record_value(item.record_type, item.value)

                    # Same SPF-duplicate rule as CREATE, applied here too —
                    # otherwise editing an unrelated TXT record into a second
                    # SPF record at a name that already has one would bypass
                    # the CREATE-only check entirely. Excludes the record
                    # being modified itself (that one's intentionally changing).
                    if item.record_type == "TXT" and _is_spf_value(new_value.get("text", "")):
                        txt_records = get_records_for_name(fqdn_clean, "TXT")
                        spf_exists = any(
                            r.ref != source.ref
                            and r.name.rstrip(".").lower() == fqdn_clean
                            and r.record_type in ("TXT", "SPF")
                            and _is_spf_value(r.data)
                            for r in txt_records
                        )
                        if spf_exists:
                            raise ValidationError(
                                "value",
                                f"An SPF record already exists for '{fqdn_raw}'. Only one SPF record is "
                                "allowed per name.",
                            )

            item_rows.append(
                DnsRequestItem(
                    request_id=request_row.id,
                    action=item.action,
                    record_type=item.record_type,
                    fqdn=fqdn_raw.rstrip("."),
                    ttl=ttl,
                    new_value=new_value,
                    expected_current_value=expected_current_value,
                    status="PENDING",
                )
            )
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"field": exc.field, "message": exc.message})

    policy_result = PolicyEngine(db).evaluate_request(zone, body.items)
    if not policy_result.allowed:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"field": "policy", "message": " ".join(policy_result.reasons) or "Rejected by policy."},
        )

    if policy_result.requires_approval:
        request_row.status = "PENDING_APPROVAL"
        db.add(ApprovalRequest(request_id=request_row.id, zone_id=zone.id, status="PENDING"))
    else:
        request_row.status = "READY_TO_EXECUTE"

    db.add_all(item_rows)
    db.commit()
    db.refresh(request_row)
    for row in item_rows:
        db.refresh(row)

    if not policy_result.requires_approval:
        trigger_execution(db, request_row.id)
        db.refresh(request_row)

    return RequestOut(
        id=request_row.id,
        zone_id=request_row.zone_id,
        status=request_row.status,
        justification=request_row.justification,
        items=[RequestItemOut.from_model(r) for r in item_rows],
        policy_reasons=policy_result.reasons,
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

    is_owner = request_row.requestor_id == user.user_id
    is_cloudops = user.has_role("CLOUDOPS_ADMIN")
    is_zone_admin = user.has_role("ZONE_ADMIN") and db.execute(
        select(ZoneAdmin.id).where(
            ZoneAdmin.zone_id == request_row.zone_id, ZoneAdmin.user_id == user.user_id
        )
    ).first() is not None
    if not (is_owner or is_cloudops or is_zone_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to view this request")

    latest_approval = (
        db.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.request_id == request_id)
            .order_by(ApprovalRequest.id.desc())
        )
        .scalars()
        .first()
    )

    return RequestOut(
        id=request_row.id,
        zone_id=request_row.zone_id,
        status=request_row.status,
        justification=request_row.justification,
        items=[RequestItemOut.from_model(r) for r in request_row.items],
        approval_request_id=latest_approval.id if latest_approval else None,
        approval_status=latest_approval.status if latest_approval else None,
    )
