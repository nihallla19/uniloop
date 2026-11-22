import httpx

from app.config import get_settings


def send_login_code(email: str, code: str) -> None:
    settings = get_settings()
    if settings.app_env == "local" and not settings.resend_api_key:
        # Local console stub only (spec 11.3). Never reached in preview or production.
        print(f"[local email stub] Uniloop code for {email}: {code}")  # noqa: T201
        return
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.email_from,
            "to": [email],
            "subject": "Your Uniloop sign-in code",
            "text": (
                f"Your Uniloop code is {code}.\n\n"
                "It works once and expires in 10 minutes. "
                "If you didn't ask for it, you can ignore this email."
            ),
        },
        timeout=10,
    )
    r.raise_for_status()
