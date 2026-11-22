import hmac

from fastapi import Header

from app.config import get_settings
from app.errors import ApiError


def require_cron(authorization: str = Header(default="")) -> None:
    secret = get_settings().cron_secret
    expected = f"Bearer {secret}"
    if not secret or not hmac.compare_digest(authorization.encode(), expected.encode()):
        raise ApiError(401, "unauthorized", "Please sign in to continue.")
