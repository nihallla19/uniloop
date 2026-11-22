"""Public catalog reads: feed rules, pagination, search safety, visibility (spec 5.5, 6.5)."""

import uuid

from sqlalchemy import text

from tests.conftest import Api, make_user


def _listing(
    engine,
    seller,
    title="Casio FX-991ES calculator",
    status="active",
    days_ago=1,
    expired=False,
    price=50000,
):  # type: ignore[no-untyped-def]
    with engine.begin() as c:
        cat = c.execute(
            text("SELECT id FROM catalog.categories ORDER BY position LIMIT 1")
        ).scalar_one()
        pp = c.execute(text("SELECT id FROM catalog.pickup_points LIMIT 1")).scalar_one()
        complete = status != "draft"
        return c.execute(
            text(
                """
                INSERT INTO catalog.listings (seller_id, category_id, pickup_point_id, title,
                    status, price_mode, price_paise, condition, published_at, expires_at)
                VALUES (:s, :c, :p, :t, :st, 'fixed', :price, CAST(:cond AS catalog.item_condition),
                    CASE WHEN :complete THEN now() - make_interval(days => :d) END,
                    CASE WHEN :complete
                         THEN now() + make_interval(days => CASE WHEN :exp THEN -1 ELSE 30 END)
                    END)
                RETURNING id
                """
            ),
            {
                "s": seller,
                "c": cat,
                "p": pp,
                "t": title,
                "st": status,
                "price": price,
                "cond": "good" if complete else None,
                "d": days_ago,
                "complete": complete,
                "exp": expired,
            },
        ).scalar_one()


def _seller(engine):  # type: ignore[no-untyped-def]
    with engine.begin() as c:
        return make_user(c)


def test_feed_shows_only_live_active(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    s = _seller(app_engine)
    live = _listing(app_engine, s)
    for status in ("draft", "reserved", "sold", "hidden", "removed"):
        _listing(app_engine, s, status=status)
    _listing(app_engine, s, expired=True)  # still 'active' until the daily job runs
    ids = [i["id"] for i in api.client.get("/api/v1/listings").json()["items"]]
    assert ids == [str(live)]


def test_cursor_pagination_no_gaps_or_dupes(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    s = _seller(app_engine)
    made = {str(_listing(app_engine, s, title=f"Item {i}", days_ago=i)) for i in range(5)}
    seen, cursor = [], None
    while True:
        params = {"limit": 2, **({"cursor": cursor} if cursor else {})}
        page = api.client.get("/api/v1/listings", params=params).json()
        seen += [i["id"] for i in page["items"]]
        if not (cursor := page["next_cursor"]):
            break
    assert len(seen) == len(set(seen)) == 5 and set(seen) == made


def test_price_sort(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    s = _seller(app_engine)
    for p in (30000, 10000, 20000):
        _listing(app_engine, s, price=p)
    prices = [
        i["price_paise"]
        for i in api.client.get("/api/v1/listings", params={"sort": "price_asc"}).json()["items"]
    ]
    assert prices == [10000, 20000, 30000]


def test_search_typo_and_injection(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    _listing(app_engine, _seller(app_engine))
    hits = api.client.get("/api/v1/listings", params={"q": "calculater"}).json()["items"]
    assert len(hits) == 1
    for evil in ["'; DROP TABLE catalog.listings; --", '" OR 1=1 --', "%' OR '1'='1", "!!!&&|"]:
        r = api.client.get("/api/v1/listings", params={"q": evil})
        assert r.status_code == 200
    assert len(api.client.get("/api/v1/listings").json()["items"]) == 1


def test_bad_inputs_rejected(api: Api) -> None:
    c = api.client
    assert c.get("/api/v1/listings", params={"sort": "id; drop"}).status_code == 422
    assert c.get("/api/v1/listings", params={"q": "x" * 101}).status_code == 422
    assert c.get("/api/v1/listings", params={"cursor": "garbage"}).status_code == 400
    assert c.get("/api/v1/listings/not-a-uuid").status_code == 404


def test_detail_visibility(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    s = _seller(app_engine)
    sold = _listing(app_engine, s, status="sold")
    draft = _listing(app_engine, s, status="draft")
    hidden = _listing(app_engine, s, status="hidden")
    r = api.client.get(f"/api/v1/listings/{sold}").json()
    assert r["status"] == "sold" and r["can_contact"] is False and "seller_id" not in r
    assert api.client.get(f"/api/v1/listings/{draft}").status_code == 404
    assert api.client.get(f"/api/v1/listings/{hidden}").status_code == 404
    assert api.client.get(f"/api/v1/listings/{uuid.uuid4()}").status_code == 404


def test_blocked_sellers_hidden_from_viewer(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    api.signup("asha@example.edu")
    s = _seller(app_engine)
    _listing(app_engine, s)
    with app_engine.begin() as c:
        viewer = c.execute(
            text("SELECT id FROM identity.users WHERE email = 'asha@example.edu'")
        ).scalar_one()
        c.execute(
            text("INSERT INTO trust.blocks (blocker_id, blocked_id) VALUES (:a, :b)"),
            {"a": s, "b": viewer},
        )
    assert api.client.get("/api/v1/listings").json()["items"] == []


def test_public_browsing_off_requires_sign_in(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    with app_engine.begin() as c:
        c.execute(
            text("UPDATE system.site_settings SET value = 'false' WHERE key = 'public_browsing'")
        )
    try:
        assert api.client.get("/api/v1/listings").status_code == 401
    finally:
        with app_engine.begin() as c:
            c.execute(
                text("UPDATE system.site_settings SET value = 'true' WHERE key = 'public_browsing'")
            )


def test_bootstrap(api: Api) -> None:
    b = api.client.get("/api/v1/catalog/bootstrap").json()
    books = next(c for c in b["categories"] if c["slug"] == "books-notes")
    assert [f["key"] for f in books["fields"]] == ["subject", "edition", "semester"]
    assert b["settings"]["public_browsing"] is True
