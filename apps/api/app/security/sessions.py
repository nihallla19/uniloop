import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, Request, Response
from sqlalchemy import Connection, text

from app.config import get_settings
from app.db import get_conn
from app.errors import ApiError

SESSION_DAYS = 30
REAUTH_MINUTES = 15


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    role: str
    session_id: uuid.UUID
    reauth_at: datetime | None


def _local() -> bool:
    return get_settings().app_env == "local"


def cookie_name() -> str:
    # Safari rejects Secure cookies on http://localhost, and __Host- requires Secure.
    return "baton_session" if _local() else "__Host-baton_session"


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def device_label(user_agent: str) -> str:
    os_name = next(
        (
            n
            for k, n in [
                ("iPhone", "iPhone"),
                ("iPad", "iPad"),
                ("Android", "Android"),
                ("Mac OS X", "Mac"),
                ("Windows", "Windows"),
                ("Linux", "Linux"),
            ]
            if k in user_agent
        ),
        "Unknown device",
    )
    browser = next(
        (
            n
            for k, n in [
                ("Edg/", "Edge"),
                ("Firefox/", "Firefox"),
                ("Chrome/", "Chrome"),
                ("Safari/", "Safari"),
            ]
            if k in user_agent
        ),
        "",
    )
    return f"{browser} on {os_name}" if browser and os_name != "Unknown device" else os_name


def create_session(conn: Connection, response: Response, user_id: uuid.UUID, ua: str) -> None:
    token = secrets.token_urlsafe(32)
    conn.execute(
        text(
            "INSERT INTO identity.sessions (user_id, token_hash, device_label, expires_at) "
            "VALUES (:u, :h, :d, now() + make_interval(days => :days))"
        ),
        {"u": user_id, "h": hash_token(token), "d": device_label(ua), "days": SESSION_DAYS},
    )
    response.set_cookie(
        cookie_name(),
        token,
        max_age=SESSION_DAYS * 86400,
        path="/",
        secure=not _local(),
        httponly=True,
        samesite="lax",
    )


def clear_cookie(response: Response) -> None:
    response.delete_cookie(
        cookie_name(), path="/", secure=not _local(), httponly=True, samesite="lax"
    )


def optional_user(request: Request, conn: Connection = Depends(get_conn)) -> CurrentUser | None:
    token = request.cookies.get(cookie_name())
    if not token:
        return None
    # Status is checked every request, so suspension takes effect immediately.
    row = conn.execute(
        text(
            """
            SELECT s.id AS session_id, s.reauth_at, u.id, u.role
            FROM identity.sessions s JOIN identity.users u ON u.id = s.user_id
            WHERE s.token_hash = :h AND s.expires_at > now() AND u.status = 'active'
            """
        ),
        {"h": hash_token(token)},
    ).first()
    if row is None:
        return None
    conn.execute(
        text(
            "UPDATE identity.sessions SET last_seen_at = now() "
            "WHERE id = :id AND last_seen_at < now() - interval '15 minutes'"
        ),
        {"id": row.session_id},
    )
    return CurrentUser(row.id, str(row.role), row.session_id, row.reauth_at)


def require_user(user: CurrentUser | None = Depends(optional_user)) -> CurrentUser:
    if user is None:
        raise ApiError(401, "unauthorized", "Please sign in to continue.")
    return user
