from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from shared.auth.session import SESSION_COOKIE_NAME
from shared.auth.tokens import decode_access_token

router = APIRouter()
templates = Jinja2Templates(directory="ui/app/templates")


def get_current_user_for_page(request: Request):
    """Like get_current_user, but returns None instead of raising — page routes
    redirect to /login rather than returning a JSON 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    if get_current_user_for_page(request):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user_for_page(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    payload = get_current_user_for_page(request)
    if not payload:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "username": payload["username"], "roles": payload["roles"]},
    )


@router.get("/requests/new", response_class=HTMLResponse)
def new_request_page(request: Request):
    payload = get_current_user_for_page(request)
    if not payload:
        return RedirectResponse("/login")
    return templates.TemplateResponse("request_new.html", {"request": request, "username": payload["username"]})


@router.get("/requests", response_class=HTMLResponse)
def my_requests_page(request: Request):
    payload = get_current_user_for_page(request)
    if not payload:
        return RedirectResponse("/login")
    return templates.TemplateResponse("requests_list.html", {"request": request, "username": payload["username"]})


@router.get("/requests/{request_id}", response_class=HTMLResponse)
def request_detail_page(request: Request, request_id: int):
    payload = get_current_user_for_page(request)
    if not payload:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "request_detail.html", {"request": request, "username": payload["username"], "request_id": request_id}
    )
