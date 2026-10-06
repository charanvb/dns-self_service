import os
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
DEFAULT_TTL_MINUTES = 60 * 8


def _signing_key() -> str:
    return os.environ["APP_AUTH_SIGNING_KEY"]


def create_access_token(user_id: int, username: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=DEFAULT_TTL_MINUTES),
    }
    return jwt.encode(payload, _signing_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure — caller must handle.
    return jwt.decode(token, _signing_key(), algorithms=[ALGORITHM])
