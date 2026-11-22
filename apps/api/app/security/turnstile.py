import httpx

from app.config import get_settings

_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify(token: str, ip: str) -> bool:
    settings = get_settings()
    if not settings.turnstile_secret_key:
        return settings.app_env == "local"
    try:
        r = httpx.post(
            _URL,
            data={"secret": settings.turnstile_secret_key, "response": token, "remoteip": ip},
            timeout=5,
        )
        return bool(r.json().get("success"))
    except (httpx.HTTPError, ValueError):
        return False
