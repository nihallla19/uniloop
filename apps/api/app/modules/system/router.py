from fastapi import APIRouter, Depends
from sqlalchemy import Connection, text

from app.db import get_conn
from app.security.cron import require_cron

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", dependencies=[Depends(require_cron)])
def ready(conn: Connection = Depends(get_conn)) -> dict[str, str]:
    conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
