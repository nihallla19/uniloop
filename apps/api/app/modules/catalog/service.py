"""Public catalog reads (spec 2.1, 5.5, 6.5). Writes arrive with the sell flow."""

import base64
import json
import uuid
from typing import Any, Literal

from sqlalchemy import Connection, text

from app.errors import ApiError
from app.security.sessions import CurrentUser

Sort = Literal["newest", "price_asc", "price_desc"]

_LIST_SELECT = """
SELECT l.id, l.title, l.price_mode, l.price_paise, l.condition, l.published_at,
       c.slug AS category_slug, c.name AS category_name, pp.name AS pickup_name,
       p.handle AS seller_handle, p.display_name AS seller_name
FROM catalog.listings l
JOIN catalog.categories c ON c.id = l.category_id
JOIN catalog.pickup_points pp ON pp.id = l.pickup_point_id
JOIN identity.profiles p ON p.user_id = l.seller_id
"""

# sort -> (ORDER BY, keyset predicate, cursor column)
_SORTS: dict[str, tuple[str, str, str]] = {
    "newest": (
        "l.published_at DESC, l.id DESC",
        "(l.published_at, l.id) < (CAST(:c_val AS timestamptz), :c_id)",
        "published_at",
    ),
    "price_asc": (
        "l.price_paise ASC, l.id ASC",
        "(l.price_paise, l.id) > (CAST(:c_val AS integer), :c_id)",
        "price_paise",
    ),
    "price_desc": (
        "l.price_paise DESC, l.id DESC",
        "(l.price_paise, l.id) < (CAST(:c_val AS integer), :c_id)",
        "price_paise",
    ),
}

_BLOCKS = """
AND NOT EXISTS (
    SELECT 1 FROM trust.blocks b
    WHERE (b.blocker_id = :viewer AND b.blocked_id = l.seller_id)
       OR (b.blocker_id = l.seller_id AND b.blocked_id = :viewer)
)
"""


def _encode_cursor(value: Any, row_id: uuid.UUID) -> str:
    raw = json.dumps([value.isoformat() if hasattr(value, "isoformat") else value, str(row_id)])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[Any, uuid.UUID]:
    try:
        value, row_id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return value, uuid.UUID(row_id)
    except (ValueError, TypeError) as exc:
        raise ApiError(400, "bad_cursor", "Please reload the page.") from exc


def _setting(conn: Connection, key: str) -> Any:
    return conn.execute(
        text("SELECT value FROM system.site_settings WHERE key = :k"), {"k": key}
    ).scalar()


def _check_public_browsing(conn: Connection, user: CurrentUser | None) -> None:
    if user is None and _setting(conn, "public_browsing") is False:
        raise ApiError(401, "unauthorized", "Please sign in to browse.")


def bootstrap(conn: Connection) -> dict[str, Any]:
    categories = conn.execute(
        text(
            """
            SELECT c.id, c.slug, c.name, c.icon,
                   COALESCE(json_agg(json_build_object(
                       'key', f.key, 'label', f.label, 'hint', f.hint,
                       'input_type', f.input_type, 'options', f.options,
                       'is_required', f.is_required) ORDER BY f.position)
                   FILTER (WHERE f.id IS NOT NULL), '[]') AS fields
            FROM catalog.categories c
            LEFT JOIN catalog.category_fields f ON f.category_id = c.id
            WHERE c.is_active GROUP BY c.id ORDER BY c.position
            """
        )
    )
    pickups = conn.execute(
        text("SELECT id, name FROM catalog.pickup_points WHERE is_active ORDER BY position, name")
    )
    settings: dict[str, Any] = {
        k: v
        for k, v in conn.execute(
            text(
                "SELECT key, value FROM system.site_settings "
                "WHERE key IN ('campus_name', 'public_browsing', 'notice_banner')"
            )
        ).tuples()
    }
    return {
        "categories": [dict(r._mapping) for r in categories],
        "pickup_points": [dict(r._mapping) for r in pickups],
        "settings": settings,
    }


def list_listings(
    conn: Connection,
    user: CurrentUser | None,
    *,
    q: str | None,
    category: str | None,
    sort: Sort,
    cursor: str | None,
    limit: int,
) -> dict[str, Any]:
    _check_public_browsing(conn, user)
    where = ["l.status = 'active'", "l.expires_at > now()"]
    params: dict[str, Any] = {"limit": limit + 1}
    if category:
        where.append("c.slug = :category")
        params["category"] = category
    if user is not None:
        params["viewer"] = user.id
    blocks = _BLOCKS if user is not None else ""

    if q:
        # Full-text matches rank above typo (trigram) matches.
        # ponytail: relevance results are a single page; add a rank+id cursor if people scroll.
        params["q"] = q
        where.append(
            "(l.search_vector @@ websearch_to_tsquery('english', :q) "
            "OR word_similarity(:q, l.title) > 0.4)"
        )
        order = (
            "ts_rank(l.search_vector, websearch_to_tsquery('english', :q)) DESC, "
            "word_similarity(:q, l.title) DESC, l.id"
        )
        cursor_col = None
    else:
        order, keyset, cursor_col = _SORTS[sort]
        if cursor:
            params["c_val"], params["c_id"] = _decode_cursor(cursor)
            where.append(keyset)

    sql = f"{_LIST_SELECT} WHERE {' AND '.join(where)} {blocks} ORDER BY {order} LIMIT :limit"
    rows = [dict(r._mapping) for r in conn.execute(text(sql), params)]  # noqa: S608
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        if cursor_col:
            next_cursor = _encode_cursor(rows[-1][cursor_col], rows[-1]["id"])
    return {"items": rows, "next_cursor": next_cursor}


_PUBLIC_STATES = {"active", "reserved", "sold", "expired"}


def get_listing(
    conn: Connection, user: CurrentUser | None, listing_id: uuid.UUID
) -> dict[str, Any]:
    _check_public_browsing(conn, user)
    row = conn.execute(
        text(
            """
            SELECT l.id, l.seller_id, l.title, l.description, l.status, l.price_mode,
                   l.price_paise, l.condition, l.availability_note, l.swap_for, l.attributes,
                   l.custom_details, l.published_at, l.expires_at, l.category_id,
                   c.slug AS category_slug, c.name AS category_name, pp.name AS pickup_name,
                   p.handle AS seller_handle, p.display_name AS seller_name,
                   u.created_at AS seller_joined,
                   (SELECT count(*) FROM catalog.listings s
                    WHERE s.seller_id = l.seller_id AND s.status = 'sold') AS seller_sold_count
            FROM catalog.listings l
            JOIN identity.users u ON u.id = l.seller_id
            JOIN identity.profiles p ON p.user_id = l.seller_id
            LEFT JOIN catalog.categories c ON c.id = l.category_id
            LEFT JOIN catalog.pickup_points pp ON pp.id = l.pickup_point_id
            WHERE l.id = :id
            """
        ),
        {"id": listing_id},
    ).first()
    if row is None:
        raise ApiError(404, "not_found", "We couldn't find that.")
    is_owner = user is not None and user.id == row.seller_id
    is_mod = user is not None and user.role in ("moderator", "admin")
    status = str(row.status)
    visible = status in _PUBLIC_STATES or is_owner or (is_mod and status in ("hidden", "removed"))
    if not visible:
        raise ApiError(404, "not_found", "We couldn't find that.")

    labels: dict[str, str] = {
        k: v
        for k, v in conn.execute(
            text("SELECT key, label FROM catalog.category_fields WHERE category_id = :c"),
            {"c": row.category_id},
        ).tuples()
    }
    data = dict(row._mapping)
    data["details"] = [
        {"label": labels.get(k, k), "value": v} for k, v in (row.attributes or {}).items()
    ] + list(row.custom_details or [])
    data["can_contact"] = status in ("active", "reserved") and not is_owner
    for private in ("seller_id", "category_id", "attributes", "custom_details"):
        data.pop(private)
    return data
