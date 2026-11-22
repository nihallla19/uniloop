from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # Neon's pooler runs PgBouncer in transaction mode: no client pool, no prepared statements.
    return create_engine(
        get_settings().database_url,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None, "connect_timeout": 10},
    )


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency: one transaction per request, committed on success."""
    with get_engine().begin() as conn:
        yield conn
