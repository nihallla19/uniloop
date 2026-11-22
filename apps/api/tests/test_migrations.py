from alembic import command
from sqlalchemy import Connection, text

from tests.conftest import alembic_config


def test_downgrade_then_upgrade_on_seeded_db(app_engine) -> None:  # type: ignore[no-untyped-def]
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with app_engine.begin() as conn:
        from scripts.seed import seed

        seed(conn)


def test_health(conn: Connection) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["x-content-type-options"] == "nosniff"
    assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_ready_rejects_missing_or_wrong_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    monkeypatch.setattr(get_settings(), "cron_secret", "s3cret")
    client = TestClient(app)
    assert client.get("/api/v1/health/ready").status_code == 401
    assert (
        client.get("/api/v1/health/ready", headers={"Authorization": "Bearer nope"}).status_code
        == 401
    )
    body = client.get("/api/v1/health/ready").text
    assert "Traceback" not in body and "s3cret" not in body
