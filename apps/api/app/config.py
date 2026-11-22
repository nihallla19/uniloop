from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must be real in production. Everything else may stay empty locally.
_REQUIRED_IN_PRODUCTION = (
    "app_origin",
    "database_url",
    "allowed_email_domains",
    "login_code_pepper",
    "rate_limit_pepper",
    "cron_secret",
    "resend_api_key",
    "email_from",
    "turnstile_secret_key",
    "r2_account_id",
    "r2_access_key_id",
    "r2_secret_access_key",
    "r2_bucket",
    "image_base_url",
)
_NON_PRODUCTION_MARKERS = (
    "localhost",
    "127.0.0.1",
    "preview",
    "REPLACE_ME",
    "dev-only",
    "example.edu",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "preview", "production"] = "local"
    app_origin: str = "http://localhost:3000"
    database_url: str = ""
    allowed_email_domains: str = ""
    login_code_pepper: str = ""
    rate_limit_pepper: str = ""
    cron_secret: str = ""
    resend_api_key: str = ""
    email_from: str = ""
    turnstile_secret_key: str = ""
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    image_base_url: str = ""

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        missing = [k for k in _REQUIRED_IN_PRODUCTION if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing production settings: {', '.join(missing)}")
        suspect = [
            k
            for k in _REQUIRED_IN_PRODUCTION
            if any(m in getattr(self, k) for m in _NON_PRODUCTION_MARKERS)
        ]
        if suspect:
            raise ValueError(f"Non-production values in production: {', '.join(suspect)}")
        return self

    @property
    def allowed_domains(self) -> frozenset[str]:
        return frozenset(
            d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
