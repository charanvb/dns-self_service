from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shared.models.requests import DnsRequest
from shared.models.system import SystemConfig

RATE_LIMIT_CONFIG_KEY = "requestor_rate_limit_per_24h"
DEFAULT_RATE_LIMIT = 2
# Roles exempt from the rate limit — they're trusted/accountable differently
# (ZONE_ADMIN approves others' work, CLOUDOPS_ADMIN is fully trusted).
EXEMPT_ROLES = {"ZONE_ADMIN", "CLOUDOPS_ADMIN"}


class RateLimitExceeded(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(
            f"You've reached the limit of {limit} DNS request(s) per 24 hours. "
            "For urgent/additional changes today, please use Micetro directly."
        )


def get_rate_limit(session: Session) -> int:
    row = session.get(SystemConfig, RATE_LIMIT_CONFIG_KEY)
    if row is None:
        return DEFAULT_RATE_LIMIT
    try:
        return int(row.value)
    except (TypeError, ValueError):
        return DEFAULT_RATE_LIMIT


def check_request_rate_limit(session: Session, user_id: int, roles: list[str]) -> None:
    """Raises RateLimitExceeded if this user has hit their rolling-24h request
    cap. Counts per REQUEST (not per record item) — a request with many items
    still only counts once. ZONE_ADMIN/CLOUDOPS_ADMIN are exempt."""
    if EXEMPT_ROLES.intersection(roles):
        return

    limit = get_rate_limit(session)
    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    count = session.scalar(
        select(func.count())
        .select_from(DnsRequest)
        .where(DnsRequest.requestor_id == user_id, DnsRequest.created_at >= window_start)
    )
    if count >= limit:
        raise RateLimitExceeded(limit)
