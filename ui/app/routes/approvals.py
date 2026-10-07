import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auth.fastapi_deps import CurrentUser, require_roles
from shared.database.session import get_session
from shared.models.approvals import ApprovalAction, ApprovalRequest
from shared.models.auth import User
from shared.models.requests import DnsRequest
from shared.models.zones import DnsZone, ZoneAdmin

from ui.app.schemas.approvals import ApprovalActionIn, ApprovalListItemOut

logger = logging.getLogger("approvals_api")

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _administered_zone_ids(db: Session, user_id: int) -> list[int]:
    return [row[0] for row in db.execute(select(ZoneAdmin.zone_id).where(ZoneAdmin.user_id == user_id)).all()]


def _can_act_on_zone(db: Session, user: CurrentUser, zone_id: int) -> bool:
    if user.has_role("CLOUDOPS_ADMIN"):
        return True
    return zone_id in _administered_zone_ids(db, user.user_id)


@router.get("", response_model=list[ApprovalListItemOut])
def list_pending_approvals(
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("ZONE_ADMIN", "CLOUDOPS_ADMIN")),
):
    query = (
        select(ApprovalRequest, DnsRequest, DnsZone.zone_name, User.username)
        .join(DnsRequest, DnsRequest.id == ApprovalRequest.request_id)
        .join(DnsZone, DnsZone.id == ApprovalRequest.zone_id)
        .join(User, User.id == DnsRequest.requestor_id)
        .where(ApprovalRequest.status == "PENDING")
        .order_by(ApprovalRequest.created_at.asc())
    )
    if not user.has_role("CLOUDOPS_ADMIN"):
        zone_ids = _administered_zone_ids(db, user.user_id)
        if not zone_ids:
            return []
        query = query.where(ApprovalRequest.zone_id.in_(zone_ids))

    rows = db.execute(query).all()
    return [
        ApprovalListItemOut(
            approval_request_id=ar.id,
            request_id=req.id,
            zone_id=req.zone_id,
            zone_name=zone_name,
            requestor=username,
            justification=req.justification,
            created_at=ar.created_at.isoformat(),
        )
        for ar, req, zone_name, username in rows
    ]


@router.post("/{approval_request_id}/approve")
def approve_request(
    approval_request_id: int,
    body: ApprovalActionIn = ApprovalActionIn(),
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("ZONE_ADMIN", "CLOUDOPS_ADMIN")),
):
    approval = db.get(ApprovalRequest, approval_request_id)
    if approval is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if not _can_act_on_zone(db, user, approval.zone_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an administrator for this zone")
    if approval.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Approval already {approval.status.lower()}")

    request_row = db.get(DnsRequest, approval.request_id)
    approval.status = "APPROVED"
    db.add(ApprovalAction(approval_request_id=approval.id, approver_id=user.user_id, action="APPROVE"))
    # No Executor exists yet (Phase 9) — approved requests sit at
    # READY_TO_EXECUTE until that's built.
    request_row.status = "READY_TO_EXECUTE"
    db.commit()
    logger.info("approval=%s request=%s approved by user=%s", approval.id, request_row.id, user.user_id)
    return {"status": "APPROVED"}


@router.post("/{approval_request_id}/reject")
def reject_request(
    approval_request_id: int,
    body: ApprovalActionIn = ApprovalActionIn(),
    db: Session = Depends(get_session),
    user: CurrentUser = Depends(require_roles("ZONE_ADMIN", "CLOUDOPS_ADMIN")),
):
    approval = db.get(ApprovalRequest, approval_request_id)
    if approval is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if not _can_act_on_zone(db, user, approval.zone_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an administrator for this zone")
    if approval.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Approval already {approval.status.lower()}")

    request_row = db.get(DnsRequest, approval.request_id)
    approval.status = "REJECTED"
    db.add(ApprovalAction(approval_request_id=approval.id, approver_id=user.user_id, action="REJECT"))
    request_row.status = "REJECTED"
    request_row.failure_reason = body.reason or "Rejected by zone administrator."
    db.commit()
    logger.info("approval=%s request=%s rejected by user=%s", approval.id, request_row.id, user.user_id)
    return {"status": "REJECTED"}
