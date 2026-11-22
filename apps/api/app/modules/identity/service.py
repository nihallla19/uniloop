import hmac
import json
import re
import secrets
import uuid
from typing import Any

from fastapi import Response
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.db import get_engine
from app.errors import ApiError
from app.modules.identity.email import send_login_code
from app.modules.identity.schemas import Preferences, ProfilePatch, VerifyCodeIn
from app.security import codes, rate_limit
from app.security.sessions import CurrentUser, clear_cookie, create_session
from app.security.turnstile import verify as verify_turnstile

TERMS_VERSION = "2026-11-01"
PREFERENCES_VERSION = 1
GENERIC_CODE_MESSAGE = "If that address can sign in, we've sent a code. It expires in 10 minutes."
_BAD_CODE = "That code didn't work. Check it, or ask for a new one."

# Field name in ProfilePatch -> column. Anything not listed can never be written.
_PROFILE_COLUMNS = {
    "handle": "handle",
    "display_name": "display_name",
    "tagline": "tagline",
    "bio": "bio",
    "accent_hex": "accent_hex",
    "layout": "layout",
    "show_sold": "show_sold",
}


# Login ---------------------------------------------------------------------


def request_code(conn: Connection, raw_email: str, turnstile_token: str, ip: str) -> None:
    email = codes.normalize_email(raw_email)
    codes.check_domain(email)
    if not verify_turnstile(turnstile_token, ip):
        raise ApiError(400, "turnstile_failed", "Please complete the check and try again.")
    rate_limit.hit("code_email_15m", email, 3, 15 * 60)
    rate_limit.hit("code_email_day", email, 10, 86400)
    rate_limit.hit("code_ip_hour", ip, 10, 3600)

    status = conn.execute(
        text("SELECT status FROM identity.users WHERE email = :e"), {"e": email}
    ).scalar()
    if status not in (None, "active"):
        return  # Suspended accounts get the same generic response and no email.

    # Global budget below Resend Free's 100/day, so abuse fails here, not at the vendor.
    rate_limit.hit(
        "email_global_day", "all", 95, 86400, "Sign-ins are busy today. Try again tomorrow."
    )
    code = codes.new_code()
    conn.execute(
        text(
            "UPDATE identity.login_codes SET consumed_at = now() "
            "WHERE email = :e AND consumed_at IS NULL"
        ),
        {"e": email},
    )
    conn.execute(
        text(
            "INSERT INTO identity.login_codes (email, code_hash, expires_at) "
            "VALUES (:e, :h, now() + make_interval(mins => :ttl))"
        ),
        {"e": email, "h": codes.code_hash(email, code), "ttl": codes.CODE_TTL_MINUTES},
    )
    send_login_code(email, code)


def _spend_attempt(email: str) -> tuple[uuid.UUID, bytes] | None:
    """Count an attempt against the latest live code, committed even if the request fails."""
    with get_engine().begin() as c:
        row = c.execute(
            text(
                """
                UPDATE identity.login_codes SET attempts = attempts + 1
                WHERE id = (
                    SELECT id FROM identity.login_codes
                    WHERE email = :e AND consumed_at IS NULL AND expires_at > now()
                    ORDER BY created_at DESC LIMIT 1
                ) AND attempts < :max
                RETURNING id, code_hash
                """
            ),
            {"e": email, "max": codes.MAX_ATTEMPTS},
        ).first()
    return (row.id, bytes(row.code_hash)) if row else None


def _new_handle(conn: Connection, display_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")[:16] or "student"
    if len(base) < 3:
        base = f"{base}_baton"[:16]
    for _ in range(10):
        handle = f"{base}_{secrets.randbelow(10_000):04d}"
        exists = conn.execute(
            text("SELECT 1 FROM identity.profiles WHERE handle = :h"), {"h": handle}
        ).first()
        if not exists:
            return handle
    raise ApiError(409, "handle_unavailable", "Please try again.")


def verify_code(
    conn: Connection,
    data: VerifyCodeIn,
    ip: str,
    user_agent: str,
    response: Response,
    current: CurrentUser | None,
) -> dict[str, bool]:
    rate_limit.hit("verify_ip_15m", ip, 10, 15 * 60)
    email = codes.normalize_email(data.email)
    spent = _spend_attempt(email)
    if spent is None or not hmac.compare_digest(spent[1], codes.code_hash(email, data.code)):
        raise ApiError(400, "invalid_code", _BAD_CODE, {"code": _BAD_CODE})
    code_id = spent[0]

    user = conn.execute(
        text("SELECT id, status FROM identity.users WHERE email = :e"), {"e": email}
    ).first()
    new_user = user is None
    if user is None:
        missing: dict[str, str] = {}
        if not data.display_name:
            missing["display_name"] = "Tell buyers what to call you."
        if not data.accept_terms:
            missing["accept_terms"] = "Please accept the terms to join."
        if not data.confirm_age:
            missing["confirm_age"] = "Please confirm your age."
        if missing:
            # Code stays live so the person can resend with their details.
            raise ApiError(422, "signup_details_required", "Just a few details to finish.", missing)
        user_id = conn.execute(
            text(
                "INSERT INTO identity.users (email, terms_version, terms_accepted_at) "
                "VALUES (:e, :t, now()) RETURNING id"
            ),
            {"e": email, "t": TERMS_VERSION},
        ).scalar_one()
        assert data.display_name is not None
        conn.execute(
            text(
                "INSERT INTO identity.profiles (user_id, handle, display_name) VALUES (:u, :h, :d)"
            ),
            {"u": user_id, "h": _new_handle(conn, data.display_name), "d": data.display_name},
        )
    elif user.status != "active":
        raise ApiError(
            403,
            "account_unavailable",
            "This account can't sign in. Contact us if you think this is a mistake.",
        )
    else:
        user_id = user.id

    conn.execute(
        text("UPDATE identity.login_codes SET consumed_at = now() WHERE id = :id"), {"id": code_id}
    )
    if current is not None and current.id == user_id:
        # Fresh code on an existing session: re-authentication for sensitive actions.
        conn.execute(
            text("UPDATE identity.sessions SET reauth_at = now() WHERE id = :id"),
            {"id": current.session_id},
        )
    else:
        create_session(conn, response, user_id, user_agent)
    return {"new_user": new_user}


def logout(conn: Connection, user: CurrentUser, response: Response) -> None:
    conn.execute(text("DELETE FROM identity.sessions WHERE id = :id"), {"id": user.session_id})
    clear_cookie(response)


def logout_all(conn: Connection, user: CurrentUser, response: Response) -> None:
    conn.execute(text("DELETE FROM identity.sessions WHERE user_id = :u"), {"u": user.id})
    clear_cookie(response)


# Account and profile -----------------------------------------------------------


def get_me(conn: Connection, user: CurrentUser) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT u.id, u.email, u.role, u.created_at, p.handle, p.display_name, p.tagline,
                   p.bio, p.accent_hex, p.layout, p.show_sold
            FROM identity.users u JOIN identity.profiles p ON p.user_id = u.id
            WHERE u.id = :u
            """
        ),
        {"u": user.id},
    ).one()
    me = dict(row._mapping)
    me["verified_student"] = "*" not in get_settings().allowed_domains
    return me


def update_profile(conn: Connection, user: CurrentUser, patch: ProfilePatch) -> dict[str, Any]:
    values = {f: getattr(patch, f) for f in patch.model_fields_set}
    nullable = {"accent_hex"}
    for field, value in values.items():
        if value is None and field not in nullable:
            raise ApiError(
                422,
                "validation_failed",
                "Please fix the highlighted fields.",
                {field: "This can't be empty."},
            )
    if "handle" in values:
        values["handle"] = values["handle"].lower()  # citext CHECK is case-insensitive
    if values:
        sets = ", ".join(f"{_PROFILE_COLUMNS[f]} = :{f}" for f in values)
        try:
            with conn.begin_nested():
                conn.execute(
                    text(
                        f"UPDATE identity.profiles SET {sets}, updated_at = now() "  # noqa: S608
                        "WHERE user_id = :uid"
                    ),
                    {**values, "uid": user.id},
                )
        except IntegrityError as exc:
            if "profiles_handle_key" in str(exc.orig):
                raise ApiError(
                    409,
                    "handle_taken",
                    "That handle is taken.",
                    {"handle": "That handle is taken. Try another."},
                ) from None
            raise
    return get_me(conn, user)


def get_preferences(conn: Connection, user: CurrentUser) -> Preferences:
    raw = conn.execute(
        text("SELECT settings FROM identity.preferences WHERE user_id = :u"), {"u": user.id}
    ).scalar()
    return Preferences.model_validate(raw or {})


def put_preferences(conn: Connection, user: CurrentUser, prefs: Preferences) -> Preferences:
    conn.execute(
        text(
            """
            INSERT INTO identity.preferences (user_id, version, settings)
            VALUES (:u, :v, CAST(:s AS jsonb))
            ON CONFLICT (user_id)
            DO UPDATE SET version = EXCLUDED.version, settings = EXCLUDED.settings,
                          updated_at = now()
            """
        ),
        {"u": user.id, "v": PREFERENCES_VERSION, "s": json.dumps(prefs.model_dump(mode="json"))},
    )
    return prefs


def list_sessions(conn: Connection, user: CurrentUser) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            "SELECT id, device_label, created_at, last_seen_at FROM identity.sessions "
            "WHERE user_id = :u AND expires_at > now() ORDER BY last_seen_at DESC"
        ),
        {"u": user.id},
    )
    return [{**r._mapping, "current": r.id == user.session_id} for r in rows]


def revoke_session(conn: Connection, user: CurrentUser, session_id: uuid.UUID) -> None:
    deleted = conn.execute(
        text("DELETE FROM identity.sessions WHERE id = :id AND user_id = :u RETURNING id"),
        {"id": session_id, "u": user.id},
    ).first()
    if deleted is None:
        raise ApiError(404, "not_found", "We couldn't find that.")
