from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auth.fastapi_deps import CurrentUser, get_current_user
from shared.auth.passwords import verify_password
from shared.auth.session import COOKIE_KWARGS, SESSION_COOKIE_NAME
from shared.auth.tokens import create_access_token
from shared.database.session import get_session
from shared.models.auth import User

from ui.app.schemas import LoginRequest, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserInfo)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_session)):
    user = db.execute(select(User).where(User.username == body.username)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    roles = [ur.role.name for ur in user.roles]
    token = create_access_token(user.id, user.username, roles)
    response.set_cookie(SESSION_COOKIE_NAME, token, **COOKIE_KWARGS)
    return UserInfo(user_id=user.id, username=user.username, display_name=user.display_name, roles=roles)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@router.get("/me", response_model=UserInfo)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_session)):
    user = db.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return UserInfo(
        user_id=user.id, username=user.username, display_name=user.display_name, roles=current_user.roles
    )
