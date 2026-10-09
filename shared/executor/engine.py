import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.micetro.encoding import encode
from shared.micetro.provider import MicetroProvider
from shared.models.execution import AuditLog, ExecutionLog
from shared.models.requests import DnsRequest, DnsRequestItem
from shared.models.zones import DnsZone

logger = logging.getLogger("executor")


class DriftConflictError(Exception):
    """Raised when a fresh Micetro lookup shows the record no longer matches
    the snapshot taken at request-creation time — refuse to execute rather
    than overwrite/remove a change nobody reviewed."""


def trigger_execution(db: Session, request_id: int) -> None:
    """Idempotent entry point — executes requests that are READY_TO_EXECUTE.
    Uses row-level locking (with_for_update) to prevent concurrency race
    conditions where multiple workers or duplicate approval triggers could
    execute the same request concurrently.
    """
    request = db.execute(
        select(DnsRequest).where(DnsRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()

    if request is None or request.status != "READY_TO_EXECUTE":
        return

    zone = db.get(DnsZone, request.zone_id)
    if zone is None:
        request.status = "FAILED"
        request.failure_reason = f"Referenced zone {request.zone_id} not found"
        db.commit()
        return

    _execute_items(db, request, zone)


def _execute_items(db: Session, request: DnsRequest, zone: DnsZone) -> None:
    request.status = "PROCESSING"
    db.commit()

    provider = MicetroProvider()
    pending_items = [item for item in request.items if item.status == "PENDING"]
    any_failed = False
    any_succeeded = False

    for item in pending_items:
        try:
            _execute_one_item(provider, zone, item)
            item.status = "SUCCEEDED"
            any_succeeded = True
            db.add(ExecutionLog(request_item_id=item.id, provider="micetro", result="SUCCESS"))
        except Exception as exc:
            item.status = "CONFLICT" if isinstance(exc, DriftConflictError) else "FAILED"
            item.error_message = str(exc)
            any_failed = True
            db.add(ExecutionLog(request_item_id=item.id, provider="micetro", result="FAILURE", error_message=str(exc)))

        db.add(
            AuditLog(
                request_id=request.id,
                action=f"EXECUTE_{item.action}",
                entity_type="dns_request_item",
                entity_id=str(item.id),
                new_value=item.new_value,
                extra={"status": item.status, "fqdn": item.fqdn, "record_type": item.record_type},
            )
        )
        db.commit()

    if any_failed and any_succeeded:
        request.status = "PARTIAL_FAILURE"
    elif any_failed:
        request.status = "FAILED"
    else:
        request.status = "COMPLETED"
    db.commit()


def _execute_one_item(provider: MicetroProvider, zone: DnsZone, item: DnsRequestItem) -> None:
    if item.action == "CREATE":
        _execute_create(provider, zone, item)
    elif item.action == "MODIFY":
        _execute_modify(provider, zone, item)
    elif item.action == "DELETE":
        _execute_delete(provider, zone, item)
    else:
        raise ValueError(f"Unknown action: {item.action}")


def _execute_create(provider: MicetroProvider, zone: DnsZone, item: DnsRequestItem) -> None:
    from shared.dns_provider.base import RecordDTO

    # Re-check for a duplicate right before writing — closes the TOCTOU window
    # between request creation/approval and execution (could be hours/days).
    fqdn_clean = item.fqdn.rstrip(".").lower()
    existing = provider.find_records_by_name(
        zone.micetro_ref, fqdn=item.fqdn, record_type=item.record_type, zone_name=zone.zone_name
    )
    duplicate = next(
        (r for r in existing if r.name.rstrip(".").lower() == fqdn_clean and r.record_type == item.record_type),
        None,
    )
    if duplicate is not None:
        raise DriftConflictError(
            f"A {item.record_type} record now exists at '{item.fqdn}' — created by someone else "
            "since this request was submitted."
        )

    ttl = item.ttl or 300
    data = encode(item.record_type, item.new_value or {})
    record = RecordDTO(ref="", zone_ref=zone.micetro_ref, name=item.fqdn, record_type=item.record_type, ttl=str(ttl), data=data)
    provider.create_record(zone.micetro_ref, record)


def _execute_modify(provider: MicetroProvider, zone: DnsZone, item: DnsRequestItem) -> None:
    expected = item.expected_current_value or {}
    ref = expected.get("ref")
    if not ref:
        raise RuntimeError("Missing source record reference for MODIFY")

    current = provider.get_record(ref, zone_name=zone.zone_name)
    if current.data != expected.get("value"):
        raise DriftConflictError(
            f"Record '{item.fqdn}' changed since this request was submitted — refusing to overwrite "
            "an unreviewed change. Create a new request against the current value."
        )

    ttl = item.ttl or expected.get("ttl") or 300
    data = encode(item.record_type, item.new_value or {})
    provider.modify_record(ref, {"data": data, "ttl": str(ttl)})


def _execute_delete(provider: MicetroProvider, zone: DnsZone, item: DnsRequestItem) -> None:
    expected = item.expected_current_value or {}
    ref = expected.get("ref")
    if not ref:
        raise RuntimeError("Missing source record reference for DELETE")

    current = provider.get_record(ref, zone_name=zone.zone_name)
    if current.data != expected.get("value"):
        raise DriftConflictError(
            f"Record '{item.fqdn}' changed since this request was submitted — refusing to delete to "
            "avoid removing unintended changes. Create a new request against the current value."
        )

    provider.delete_record(ref)
