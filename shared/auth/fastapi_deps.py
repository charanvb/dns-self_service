from fastapi import Depends, HTTPException, Request, status

from shared.auth.session import SESSION_COOKIE_NAME
from shared.auth.tokens import decode_access_token


class CurrentUser:
    def __init__(self, user_id: int, username: str, roles: list[str]):
        self.user_id = user_id
        self.username = username
        self.roles = roles

    def has_role(self, role: str) -> bool:
        return role in self.roles


def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return CurrentUser(user_id=int(payload["sub"]), username=payload["username"], roles=payload["roles"])


def require_roles(*allowed_roles: str):
    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(current_user.has_role(r) for r in allowed_roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return current_user

    return _check
