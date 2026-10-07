import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database.session import get_session
from shared.executor.engine import handle_backup_callback

logger = logging.getLogger("internal_api")

# NOTE: this endpoint is called by the Azure Automation runbook, not a logged-in
# browser user — it is authenticated via HMAC signature only (no session cookie,
# no IAP-compatible identity). See deployment note: the ui Cloud Run service is
# currently behind IAP, which will block this inbound call entirely until it is
# exposed through a path/service that bypasses IAP (flagged for the user).
router = APIRouter(prefix="/internal", tags=["internal"])


class BackupCallbackIn(BaseModel):
    status: str  # "success" | "failure"
    backupLocation: str | None = None
    error: str | None = None


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    secret = os.environ.get("AZURE_AUTOMATION_BACKUP_CALLBACK_SECRET", "")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/backups/{correlation_id}/complete")
async def backup_complete(
    correlation_id: str,
    request: Request,
    db: Session = Depends(get_session),
):
    raw_body = await request.body()
    if not _verify_signature(raw_body, request.headers.get("X-Signature")):
        logger.warning("rejected backup callback for correlation_id=%s: bad/missing signature", correlation_id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    body = BackupCallbackIn.model_validate_json(raw_body)
    try:
        backup = handle_backup_callback(
            db,
            correlation_id,
            succeeded=(body.status == "success"),
            backup_location=body.backupLocation,
            error=body.error,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    return {"status": backup.status}
