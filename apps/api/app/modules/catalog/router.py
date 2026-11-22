import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Connection

from app.db import get_conn
from app.modules.catalog import service
from app.security import rate_limit
from app.security.sessions import CurrentUser, optional_user

router = APIRouter()


@router.get("/catalog/bootstrap")
def bootstrap(conn: Connection = Depends(get_conn)) -> dict[str, Any]:
    return service.bootstrap(conn)


@router.get("/listings")
def list_listings(
    request: Request,
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, pattern=r"^[a-z0-9-]{2,40}$"),
    sort: service.Sort = "newest",
    cursor: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=24, ge=1, le=48),
    conn: Connection = Depends(get_conn),
    user: CurrentUser | None = Depends(optional_user),
) -> dict[str, Any]:
    q = q.strip() if q else None
    if q:
        rate_limit.hit("search_ip_min", rate_limit.client_ip(request), 60, 60)
    return service.list_listings(
        conn, user, q=q, category=category, sort=sort, cursor=cursor, limit=limit
    )


@router.get("/listings/{listing_id}")
def get_listing(
    listing_id: uuid.UUID,
    conn: Connection = Depends(get_conn),
    user: CurrentUser | None = Depends(optional_user),
) -> dict[str, Any]:
    return service.get_listing(conn, user, listing_id)
