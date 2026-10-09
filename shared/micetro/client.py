import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

# Process-level session token cache to avoid creating a new Micetro session
# on every API route invocation. Keyed by (base_url, username) -> (token, expiry_time).
_SESSION_CACHE: dict[tuple[str, str], tuple[str, float]] = {}
_SESSION_LOCK = threading.Lock()
_SESSION_TTL_SECONDS = 900  # 15 minutes


class MicetroAuthError(Exception):
    pass


class MicetroClient:
    """Thin HTTP client for the Micetro REST API v2. Handles session (bearer
    token) auth with process-level token caching — no DNS business logic here,
    see MicetroProvider."""

    def __init__(self, base_url: str | None = None, username: str | None = None, password: str | None = None):
        self.base_url = (base_url or os.environ["MICETRO_API_URL"]).rstrip("/")
        self.username = username or os.environ["MICETRO_API_USERNAME"]
        self.password = password or os.environ["MICETRO_API_PASSWORD"]

    @property
    def _cache_key(self) -> tuple[str, str]:
        return (self.base_url, self.username)

    def _login(self) -> str:
        # Not listed under "paths" in the swagger export — confirmed via the live
        # Swagger UI "Try it out" that the real path has a "/micetro/" prefix.
        url = f"{self.base_url}/micetro/sessions"
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    url,
                    json={"loginName": self.username, "password": self.password},
                    timeout=30,
                )
                resp.raise_for_status()
                body = resp.json()
                # Confirmed response shape: {"result": {"session": "..."}}.
                token = body.get("session") or body.get("result", {}).get("session")
                if not token:
                    raise MicetroAuthError(f"Unexpected /micetro/sessions response shape: {body!r}")
                return token
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                logger.warning(
                    "Micetro login attempt %d/%d to %s timed out or connection failed: %s",
                    attempt,
                    max_attempts,
                    url,
                    exc,
                )
                if attempt == max_attempts:
                    logger.error("All %d Micetro login attempts to %s failed", max_attempts, url)
                    raise
                time.sleep(2 * attempt)
            except requests.exceptions.HTTPError as exc:
                logger.error("Micetro login failed with HTTP error: %s", exc)
                raise

    def _invalidate_cached_token(self) -> None:
        with _SESSION_LOCK:
            _SESSION_CACHE.pop(self._cache_key, None)

    def _ensure_token(self) -> str:
        now = time.time()
        cached = _SESSION_CACHE.get(self._cache_key)
        if cached:
            token, expiry = cached
            if now < expiry:
                return token

        with _SESSION_LOCK:
            # Double-check inside lock
            cached = _SESSION_CACHE.get(self._cache_key)
            if cached:
                token, expiry = cached
                if time.time() < expiry:
                    return token

            token = self._login()
            _SESSION_CACHE[self._cache_key] = (token, time.time() + _SESSION_TTL_SECONDS)
            return token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        token = self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            logger.warning("Micetro request %s %s failed on first attempt: %s. Retrying once...", method, url, exc)
            time.sleep(1)
            resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if resp.status_code == 401:
            # Session likely expired or revoked — invalidate cache, re-login once and retry.
            logger.info("Micetro returned 401 Unauthorized; invalidating session cache and retrying")
            self._invalidate_cached_token()
            token = self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            # Default message omits the response body, which is where Micetro
            # actually explains the rejection (e.g. naming conflict details).
            raise requests.exceptions.HTTPError(f"{exc} — response body: {resp.text[:1000]}", response=resp) from exc
        return resp

    def get(self, path: str, **kwargs) -> dict:
        body = self.request("GET", path, **kwargs).json()
        # Real API responses are wrapped in {"result": {...}} even where the
        # swagger schema shows a flat object — confirmed empirically, not just
        # for /sessions. Unwrap once here so callers always see a flat dict.
        return body.get("result", body) if isinstance(body, dict) else body

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
