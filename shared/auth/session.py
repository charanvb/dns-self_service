SESSION_COOKIE_NAME = "dns_self_service_session"

# Cookie flags: httpOnly (no JS access), secure (HTTPS only — Cloud Run is always
# HTTPS), SameSite=Lax (sent on top-level navigation, blocks most CSRF vectors).
COOKIE_KWARGS = {
    "httponly": True,
    "secure": True,
    "samesite": "lax",
    "path": "/",
}
