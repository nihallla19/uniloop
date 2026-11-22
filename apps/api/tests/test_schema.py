"""Schema shape, role permissions and constraints from spec sections 5.3 and 5.7."""

import uuid

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from tests.conftest import make_user

SPEC_TABLES = {
    "identity.users",
    "identity.sessions",
    "identity.login_codes",
    "identity.profiles",
    "identity.preferences",
    "media.assets",
    "catalog.categories",
    "catalog.category_fields",
    "catalog.pickup_points",
    "catalog.listings",
    "catalog.listing_images",
    "catalog.favorites",
    "messaging.conversations",
    "messaging.messages",
    "trust.reports",
    "trust.blocks",
    "trust.moderation_actions",
    "system.site_settings",
    "system.rate_limits",
}


def fails(conn: Connection, sql: str, params: dict | None = None, exc=IntegrityError) -> None:
    with pytest.raises(exc), conn.begin_nested():
        conn.execute(text(sql), params or {})


def ids(conn: Connection) -> dict[str, uuid.UUID]:
    return {
        "category": conn.execute(text("SELECT id FROM catalog.categories LIMIT 1")).scalar_one(),
        "pickup": conn.execute(text("SELECT id FROM catalog.pickup_points LIMIT 1")).scalar_one(),
    }


# Shape -------------------------------------------------------------------


def test_tables_match_spec_exactly(conn: Connection) -> None:
    rows = conn.execute(
        text(
            "SELECT schemaname || '.' || tablename FROM pg_tables "
            "WHERE schemaname IN ('identity','media','catalog','messaging','trust','system')"
        )
    ).scalars()
    assert set(rows) - {"system.alembic_version"} == SPEC_TABLES


def test_seed_matches_spec(conn: Connection) -> None:
    assert conn.execute(text("SELECT count(*) FROM catalog.categories")).scalar_one() == 10
    keys = set(conn.execute(text("SELECT key FROM system.site_settings")).scalars())
    assert keys == {
        "campus_name",
        "public_browsing",
        "listing_expiry_days",
        "max_active_listings",
        "notice_banner",
    }


# Roles (5.7) -------------------------------------------------------------


def test_app_cannot_read_alembic_version(conn: Connection) -> None:
    fails(conn, "SELECT * FROM system.alembic_version", exc=ProgrammingError)


def test_app_has_no_ddl(conn: Connection) -> None:
    fails(conn, "CREATE TABLE catalog.sneaky (id int)", exc=ProgrammingError)


def test_moderation_actions_append_only(conn: Connection) -> None:
    actor = make_user(conn)
    conn.execute(
        text("INSERT INTO trust.moderation_actions (actor_id, action) VALUES (:a, 'warn')"),
        {"a": actor},
    )
    fails(conn, "UPDATE trust.moderation_actions SET note = 'x'", exc=ProgrammingError)
    fails(conn, "DELETE FROM trust.moderation_actions", exc=ProgrammingError)


# Identity ----------------------------------------------------------------


def test_email_unique_case_insensitive(conn: Connection) -> None:
    make_user(conn, "alice_1")
    fails(
        conn,
        "INSERT INTO identity.users (email, terms_version, terms_accepted_at) "
        "VALUES ('ALICE_1@EXAMPLE.EDU', 'v1', now())",
    )


@pytest.mark.parametrize("handle", ["ab", "has space", "x" * 25, "dash-ed"])
def test_handle_pattern(conn: Connection, handle: str) -> None:
    fails(
        conn,
        "INSERT INTO identity.profiles (user_id, handle, display_name) "
        "VALUES (gen_random_uuid(), :h, 'X')",
        {"h": handle},
    )


def test_accent_hex_pattern(conn: Connection) -> None:
    user = make_user(conn)
    fails(
        conn, "UPDATE identity.profiles SET accent_hex = 'red;bad' WHERE user_id = :u", {"u": user}
    )
    conn.execute(
        text("UPDATE identity.profiles SET accent_hex = '#0A84ff' WHERE user_id = :u"), {"u": user}
    )


def test_login_code_attempts_capped(conn: Connection) -> None:
    fails(
        conn,
        "INSERT INTO identity.login_codes (email, code_hash, attempts, expires_at) "
        "VALUES ('a@b.c', '\\x00', 6, now())",
    )


def test_preferences_must_be_object(conn: Connection) -> None:
    user = make_user(conn)
    fails(
        conn, "INSERT INTO identity.preferences (user_id, settings) VALUES (:u, '[]')", {"u": user}
    )


# Listings ----------------------------------------------------------------


def test_empty_draft_is_allowed(conn: Connection) -> None:
    seller = make_user(conn)
    conn.execute(text("INSERT INTO catalog.listings (seller_id) VALUES (:s)"), {"s": seller})


def test_publish_requires_complete_listing(conn: Connection) -> None:
    seller = make_user(conn)
    fails(
        conn,
        "INSERT INTO catalog.listings (seller_id, status, title) "
        "VALUES (:s, 'active', 'Calculator')",
        {"s": seller},
    )


def _active(conn: Connection, seller: uuid.UUID, mode: str, price: int) -> None:
    ref = ids(conn)
    conn.execute(
        text(
            """
            INSERT INTO catalog.listings (seller_id, status, title, category_id, pickup_point_id,
                condition, price_mode, price_paise, published_at, expires_at)
            VALUES (:s, 'active', 'Casio FX-991ES', :c, :p, 'good', :m, :price,
                now(), now() + interval '60 days')
            """
        ),
        {"s": seller, "c": ref["category"], "p": ref["pickup"], "m": mode, "price": price},
    )


def test_complete_listing_publishes(conn: Connection) -> None:
    _active(conn, make_user(conn), "fixed", 50000)


@pytest.mark.parametrize(
    ("mode", "price"),
    [("free", 100), ("swap", 1), ("fixed", 0), ("negotiable", 0), ("fixed", 100000001)],
)
def test_price_rules(conn: Connection, mode: str, price: int) -> None:
    seller = make_user(conn)
    with pytest.raises(IntegrityError), conn.begin_nested():
        _active(conn, seller, mode, price)


def test_custom_details_must_be_array(conn: Connection) -> None:
    fails(
        conn,
        "INSERT INTO catalog.listings (seller_id, custom_details) VALUES (:s, '{}')",
        {"s": make_user(conn)},
    )


def test_search_vector_is_generated(conn: Connection) -> None:
    _active(conn, make_user(conn), "fixed", 50000)
    hit = conn.execute(
        text(
            "SELECT count(*) FROM catalog.listings "
            "WHERE search_vector @@ websearch_to_tsquery('english', 'casio')"
        )
    ).scalar_one()
    assert hit == 1


# Images ------------------------------------------------------------------


def _asset(conn: Connection, owner: uuid.UUID) -> uuid.UUID:
    return conn.execute(
        text(
            "INSERT INTO media.assets (owner_id, kind, storage_prefix, width, height, "
            "size_bytes, placeholder) VALUES (:o, 'listing', :p, 800, 600, 1000, 'x') RETURNING id"
        ),
        {"o": owner, "p": f"local/listing/{uuid.uuid4()}"},
    ).scalar_one()


def test_image_positions(conn: Connection) -> None:
    seller = make_user(conn)
    listing = conn.execute(
        text("INSERT INTO catalog.listings (seller_id) VALUES (:s) RETURNING id"), {"s": seller}
    ).scalar_one()
    a, b = _asset(conn, seller), _asset(conn, seller)
    insert = "INSERT INTO catalog.listing_images VALUES (:l, :a, :pos)"
    conn.execute(text(insert), {"l": listing, "a": a, "pos": 0})
    conn.execute(text(insert), {"l": listing, "a": b, "pos": 1})
    fails(conn, insert, {"l": listing, "a": _asset(conn, seller), "pos": 8})

    # Deferred uniqueness lets a reorder swap positions inside one transaction.
    with conn.begin_nested():
        conn.execute(
            text("UPDATE catalog.listing_images SET position = 1 - position WHERE listing_id = :l"),
            {"l": listing},
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    with pytest.raises(IntegrityError), conn.begin_nested():
        conn.execute(
            text("UPDATE catalog.listing_images SET position = 0 WHERE listing_id = :l"),
            {"l": listing},
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


# Messaging and trust -----------------------------------------------------


def test_message_body_and_nonce(conn: Connection) -> None:
    seller, buyer = make_user(conn), make_user(conn)
    listing = conn.execute(
        text("INSERT INTO catalog.listings (seller_id) VALUES (:s) RETURNING id"), {"s": seller}
    ).scalar_one()
    convo = conn.execute(
        text(
            "INSERT INTO messaging.conversations (listing_id, buyer_id) VALUES (:l, :b) "
            "RETURNING id"
        ),
        {"l": listing, "b": buyer},
    ).scalar_one()
    insert = (
        "INSERT INTO messaging.messages (conversation_id, sender_id, client_nonce, body) "
        "VALUES (:c, :s, :n, :body)"
    )
    nonce = uuid.uuid4()
    conn.execute(text(insert), {"c": convo, "s": buyer, "n": nonce, "body": "Hi"})
    fails(conn, insert, {"c": convo, "s": buyer, "n": nonce, "body": "Hi again"})
    fails(conn, insert, {"c": convo, "s": buyer, "n": uuid.uuid4(), "body": ""})
    fails(conn, insert, {"c": convo, "s": buyer, "n": uuid.uuid4(), "body": "x" * 2001})
    fails(
        conn,
        "INSERT INTO messaging.conversations (listing_id, buyer_id) VALUES (:l, :b)",
        {"l": listing, "b": buyer},
    )


def test_cannot_block_self(conn: Connection) -> None:
    user = make_user(conn)
    fails(conn, "INSERT INTO trust.blocks (blocker_id, blocked_id) VALUES (:u, :u)", {"u": user})


def test_report_reason_allowlist(conn: Connection) -> None:
    fails(
        conn,
        "INSERT INTO trust.reports (reporter_id, reason) VALUES (:u, 'bored')",
        {"u": make_user(conn)},
    )
