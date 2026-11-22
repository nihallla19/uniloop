"""Passwordless login code helpers (spec 7.1)."""

import hashlib
import hmac
import secrets

from app.config import get_settings
from app.errors import ApiError

CODE_TTL_MINUTES = 10
MAX_ATTEMPTS = 5


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    local, _, domain = email.rpartition("@")
    if (
        not email.isascii()
        or not local
        or "." not in domain
        or any(c.isspace() for c in email)
        or len(email) > 254
    ):
        raise ApiError(
            422,
            "validation_failed",
            "Please fix the highlighted fields.",
            {"email": "Enter a valid email address, like you@college.edu."},
        )
    return email


def check_domain(email: str) -> None:
    allowed = get_settings().allowed_domains
    if "*" in allowed:
        return
    local, _, domain = email.rpartition("@")
    if domain not in allowed:
        raise ApiError(
            422,
            "validation_failed",
            "Please fix the highlighted fields.",
            {"email": "Use your college email address."},
        )
    if "+" in local:
        raise ApiError(
            422,
            "validation_failed",
            "Please fix the highlighted fields.",
            {"email": "Use your college email without a + tag."},
        )


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def code_hash(email: str, code: str) -> bytes:
    pepper = get_settings().login_code_pepper.encode()
    return hmac.new(pepper, (email + code).encode(), hashlib.sha256).digest()
