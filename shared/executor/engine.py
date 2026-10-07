import logging
import os
import uuid

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.micetro.encoding import encode
from shared.micetro.provider import MicetroProvider
from shared.models.execution import AuditLog, DnsZoneBackup, ExecutionLog
from shared.models.requests import DnsRequest, DnsRequestItem
from shared.models.zones import DnsZone

logger = logging.getLogger("executor")


class DriftConflictError(Exception):
    """Raised when a fresh Micetro lookup shows the record no longer matches
    the snapshot taken at request-creation time — refuse to execute rather
    than overwrite/remove a change nobody reviewed."""


def trigger_execution(db: Session, request_id: int) -> None:
    """Idempotent entry point — safe to call multiple times for the same
    request (e.g. once on approval, again if a backup callback resumes it).
    Only acts when the request is actually at READY_TO_EXECUTE/
    BACKUP_IN_PROGRESS; any other status is a no-op."""
    request = db.get(DnsRequest, request_id)
    if request is None or request.status not in ("READY_TO_EXECUTE", "BACKUP_IN_PROGRESS"):
        return
    zone = db.get(DnsZone, request.zone_id)

    backup = db.execute(
        select(DnsZoneBackup)
        .where(DnsZoneBackup.request_id == request_id)
        .order_by(DnsZoneBackup.id.desc())
    ).scalars().first()

    if backup is None:
        backup = _trigger_backup(db, request, zone)
        request.status = "BACKUP_IN_PROGRESS" if backup.status == "TRIGGERED" else "BACKUP_FAILED"
        if backup.status != "TRIGGERED":
            request.failure_reason = backup.error_message
        db.commit()
        return

    if backup.status == "TRIGGERED":
        return  # still waiting on the Azure Automation callback

    if backup.status in ("FAILED", "TIMEOUT"):
        request.status = "BACKUP_FAILED"
        request.failure_reason = backup.error_message or f"Zone backup {backup.status.lower()}"
        db.commit()
        return

    _execute_items(db, request, zone)


def _trigger_backup(db: Session, request: DnsRequest, zone: DnsZone) -> DnsZoneBackup:
    correlation_id = str(uuid.uuid4())
    backup = DnsZoneBackup(request_id=request.id, zone_id=zone.id, correlation_id=correlation_id, status="TRIGGERED")
    db.add(backup)
    db.flush()

    callback_base = os.environ.get("APP_CALLBACK_BASE_URL", "").rstrip("/")
    try:
        webhook_url = os.environ["AZURE_AUTOMATION_BACKUP_WEBHOOK_URL"]
        resp = requests.post(
            webhook_url,
            json={
                "zoneName": zone.zone_name,
                "correlationId": correlation_id,
                "callbackUrl": f"{callback_base}/internal/backups/{correlation_id}/complete",
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json() if resp.content else {}
        backup.azure_job_id = str(body.get("jobId") or body.get("id") or "") or None
    except Exception as exc:
        logger.error("backup trigger failed for request=%s zone=%s: %s", request.id, zone.zone_name, exc)
        backup.status = "FAILED"
        backup.error_message = f"Failed to trigger zone backup: {exc}"
    return backup


def handle_backup_callback(
    db: Session, correlation_id: str, succeeded: bool, backup_location: str | None, error: str | None
) -> DnsZoneBackup:
    backup = db.execute(
        select(DnsZoneBackup).where(DnsZoneBackup.correlation_id == correlation_id)
    ).scalar_one_or_none()
    if backup is None:
        raise ValueError(f"Unknown backup correlationId: {correlation_id}")
    if backup.status != "TRIGGERED":
        return backup  # already processed — ignore a duplicate/late callback

    from shared.models.mixins import utcnow

    backup.status = "COMPLETED" if succeeded else "FAILED"
    backup.backup_location = backup_location
    backup.error_message = error
    backup.completed_at = utcnow()
    db.commit()

    trigger_execution(db, backup.request_id)
    return backup


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
    existing = provider.list_all_records(zone.micetro_ref, zone_name=zone.zone_name)
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
