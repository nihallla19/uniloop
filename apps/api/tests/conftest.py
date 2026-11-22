import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.pool import NullPool

from scripts.seed import seed

MIGRATOR_URL = os.environ.get(
    "TEST_DATABASE_URL_DIRECT",
    "postgresql+psycopg://baton_migrator:migrator@localhost:5432/baton_test",
)
APP_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://baton_app:app@localhost:5432/baton_test"
)
API_ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://localhost:3000"

# Point the app at the test database before anything reads settings.
os.environ.update(
    APP_ENV="local",
    APP_ORIGIN=ORIGIN,
    DATABASE_URL=APP_URL,
    ALLOWED_EMAIL_DOMAINS="example.edu",
    LOGIN_CODE_PEPPER="test-login-pepper",
    RATE_LIMIT_PEPPER="test-rate-pepper",
    TURNSTILE_SECRET_KEY="",
    RESEND_API_KEY="",
)


def alembic_config() -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", MIGRATOR_URL)
    return cfg


def reset_database() -> None:
    engine = create_engine(MIGRATOR_URL, poolclass=NullPool)
    with engine.begin() as conn:
        conn.execute(
            text("DROP SCHEMA IF EXISTS identity, media, catalog, messaging, trust, system CASCADE")
        )
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine():  # type: ignore[no-untyped-def]
    reset_database()
    command.upgrade(alembic_config(), "head")
    engine = create_engine(APP_URL, poolclass=NullPool, connect_args={"prepare_threshold": None})
    with engine.begin() as conn:
        seed(conn)
    yield engine
    engine.dispose()


@pytest.fixture
def conn(app_engine) -> Iterator[Connection]:  # type: ignore[no-untyped-def]
    """App-role connection whose work is rolled back after each test."""
    with app_engine.connect() as c:
        tx = c.begin()
        yield c
        tx.rollback()


def make_user(conn: Connection, handle: str | None = None) -> uuid.UUID:
    handle = handle or "u" + uuid.uuid4().hex[:10]
    user_id = conn.execute(
        text(
            "INSERT INTO identity.users (email, terms_version, terms_accepted_at) "
            "VALUES (:email, 'v1', now()) RETURNING id"
        ),
        {"email": f"{handle}@example.edu"},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO identity.profiles (user_id, handle, display_name) "
            "VALUES (:id, :handle, 'Test')"
        ),
        {"id": user_id, "handle": handle},
    )
    return user_id


def truncate_runtime_tables() -> None:
    engine = create_engine(MIGRATOR_URL, poolclass=NullPool)
    with engine.begin() as c:
        c.execute(text("TRUNCATE identity.users, identity.login_codes, system.rate_limits CASCADE"))
        seed(c)  # CASCADE also clears site_settings (updated_by -> users)
    engine.dispose()


class Api:
    """TestClient wrapper that captures emailed codes and sends CSRF headers."""

    def __init__(self, sent: dict[str, str]) -> None:
        from fastapi.testclient import TestClient

        from app.main import app

        self.sent = sent
        self.client = TestClient(app, headers={"X-Baton-Client": "web", "Origin": ORIGIN})

    def signup(self, email: str, name: str = "Asha") -> dict:  # type: ignore[type-arg]
        assert (
            self.client.post("/api/v1/auth/request-code", json={"email": email}).status_code == 200
        )
        r = self.client.post(
            "/api/v1/auth/verify-code",
            json={
                "email": email,
                "code": self.sent[email],
                "display_name": name,
                "accept_terms": True,
                "confirm_age": True,
            },
        )
        assert r.status_code == 200, r.text
        return r.json()


@pytest.fixture
def api(app_engine, monkeypatch) -> Api:  # type: ignore[no-untyped-def]
    from app.modules.identity import service

    truncate_runtime_tables()
    sent: dict[str, str] = {}
    monkeypatch.setattr(service, "send_login_code", lambda e, c: sent.__setitem__(e, c))
    monkeypatch.setattr(service, "verify_turnstile", lambda t, ip: True)
    return Api(sent)
