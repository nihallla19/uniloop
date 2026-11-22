import hashlib
import hmac
import math
import time

from fastapi import Request
from sqlalchemy import text

from app.config import get_settings
from app.db import get_engine
from app.errors import ApiError


def client_ip(request: Request) -> str:
    # Vercel overwrites these headers, so they are trustworthy only behind Vercel.
    if get_settings().app_env != "local":
        ip = request.headers.get("x-vercel-forwarded-for") or request.headers.get("x-real-ip")
        if ip:
            return ip.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bucket(action: str, ident: str) -> str:
    pepper = get_settings().rate_limit_pepper.encode()
    return f"{action}:{hmac.new(pepper, ident.encode(), hashlib.sha256).hexdigest()[:32]}"


def hit(action: str, ident: str, limit: int, window_s: int, message: str | None = None) -> None:
    """Count one hit in a fixed window; raise 429 once the limit is passed."""
    now = time.time()
    start = math.floor(now / window_s) * window_s
    # Own transaction so the count survives when the request itself fails.
    with get_engine().begin() as conn:
        hits = conn.execute(
            text(
                """
                INSERT INTO system.rate_limits (bucket, window_start)
                VALUES (:b, to_timestamp(:s))
                ON CONFLICT (bucket, window_start)
                DO UPDATE SET hits = system.rate_limits.hits + 1
                RETURNING hits
                """
            ),
            {"b": _bucket(action, ident), "s": start},
        ).scalar_one()
    if hits > limit:
        raise ApiError(
            429,
            "rate_limited",
            message or "Too many tries. Please wait a moment.",
            headers={"Retry-After": str(int(start + window_s - now) + 1)},
        )
