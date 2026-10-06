import logging
import os

import requests

logger = logging.getLogger(__name__)


class MicetroAuthError(Exception):
    pass


class MicetroClient:
    """Thin HTTP client for the Micetro REST API v2. Handles session (bearer
    token) auth only — no DNS business logic here, see MicetroProvider."""

    def __init__(self, base_url: str | None = None, username: str | None = None, password: str | None = None):
        self.base_url = (base_url or os.environ["MICETRO_API_URL"]).rstrip("/")
        self.username = username or os.environ["MICETRO_API_USERNAME"]
        self.password = password or os.environ["MICETRO_API_PASSWORD"]
        self._session_token: str | None = None

    def _login(self) -> str:
        # Not listed under "paths" in the swagger export — confirmed via the live
        # Swagger UI "Try it out" that the real path has a "/micetro/" prefix.
        resp = requests.post(
            f"{self.base_url}/micetro/sessions",
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

    def _ensure_token(self) -> str:
        if self._session_token is None:
            self._session_token = self._login()
        return self._session_token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        token = self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.request(method, f"{self.base_url}{path}", headers=headers, timeout=30, **kwargs)
        if resp.status_code == 401:
            # Session likely expired — re-login once and retry.
            self._session_token = None
            token = self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.request(method, f"{self.base_url}{path}", headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
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
