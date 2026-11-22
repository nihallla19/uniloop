import os

from fastapi import Request

from app.config import get_settings
from app.errors import ApiError

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _allowed_origins() -> set[str]:
    settings = get_settings()
    origins = {settings.app_origin}
    if settings.app_env == "preview":
        for var in ("VERCEL_URL", "VERCEL_BRANCH_URL"):
            if host := os.environ.get(var):
                origins.add(f"https://{host}")
    return origins


def require_same_origin(request: Request) -> None:
    """App-wide dependency (spec 7.3): state changes need our header and our origin."""
    if request.method in _SAFE_METHODS:
        return
    if (
        request.headers.get("x-baton-client") != "web"
        or request.headers.get("origin") not in _allowed_origins()
    ):
        raise ApiError(403, "csrf_failed", "Please refresh the page and try again.")
