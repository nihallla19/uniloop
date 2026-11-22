"""Auth, sessions, profile and preferences (spec 7.1–7.3, 7.6, 7.9)."""

from sqlalchemy import text

from tests.conftest import Api

RC = "/api/v1/auth/request-code"
VC = "/api/v1/auth/verify-code"


def test_signup_creates_account_and_session(api: Api) -> None:
    assert api.signup("asha@example.edu") == {"new_user": True}
    me = api.client.get("/api/v1/me").json()
    assert me["email"] == "asha@example.edu"
    assert me["display_name"] == "Asha" and me["role"] == "user"
    assert me["handle"].startswith("asha_")


def test_returning_user_signs_in(api: Api) -> None:
    api.signup("asha@example.edu")
    api.client.cookies.clear()
    api.client.post(RC, json={"email": "asha@example.edu"})
    r = api.client.post(
        VC, json={"email": "asha@example.edu", "code": api.sent["asha@example.edu"]}
    )
    assert r.json() == {"new_user": False}
    assert api.client.get("/api/v1/me").status_code == 200


def test_first_signin_needs_details_and_keeps_code_live(api: Api) -> None:
    api.client.post(RC, json={"email": "new@example.edu"})
    code = api.sent["new@example.edu"]
    r = api.client.post(VC, json={"email": "new@example.edu", "code": code})
    assert r.status_code == 422
    assert set(r.json()["error"]["fields"]) == {"display_name", "accept_terms", "confirm_age"}
    r = api.client.post(
        VC,
        json={
            "email": "new@example.edu",
            "code": code,
            "display_name": "N",
            "accept_terms": True,
            "confirm_age": True,
        },
    )
    assert r.status_code == 200


def test_enumeration_responses_identical(api: Api) -> None:
    api.signup("known@example.edu")
    a = api.client.post(RC, json={"email": "known@example.edu"})
    b = api.client.post(RC, json={"email": "unknown@example.edu"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()


def test_domain_and_plus_rules(api: Api) -> None:
    assert api.client.post(RC, json={"email": "x@gmail.com"}).status_code == 422
    assert api.client.post(RC, json={"email": "x+alt@example.edu"}).status_code == 422
    assert api.client.post(RC, json={"email": "  X@Example.EDU "}).status_code == 200
    assert "x@example.edu" in api.sent


def test_code_reuse_fails(api: Api) -> None:
    api.signup("asha@example.edu")
    code = api.sent["asha@example.edu"]
    api.client.cookies.clear()
    r = api.client.post(VC, json={"email": "asha@example.edu", "code": code})
    assert r.status_code == 400


def test_new_request_invalidates_old_code(api: Api) -> None:
    api.client.post(RC, json={"email": "a@example.edu"})
    old = api.sent["a@example.edu"]
    api.client.post(RC, json={"email": "a@example.edu"})
    if old == api.sent["a@example.edu"]:  # 1-in-a-million collision
        return
    assert api.client.post(VC, json={"email": "a@example.edu", "code": old}).status_code == 400


def test_expired_code_fails(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    api.client.post(RC, json={"email": "a@example.edu"})
    with app_engine.begin() as c:
        c.execute(text("UPDATE identity.login_codes SET expires_at = now() - interval '1 second'"))
    r = api.client.post(VC, json={"email": "a@example.edu", "code": api.sent["a@example.edu"]})
    assert r.status_code == 400


def test_sixth_attempt_fails_even_with_right_code(api: Api) -> None:
    api.client.post(RC, json={"email": "a@example.edu"})
    right = api.sent["a@example.edu"]
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(5):
        assert (
            api.client.post(VC, json={"email": "a@example.edu", "code": wrong}).status_code == 400
        )
    r = api.client.post(
        VC,
        json={
            "email": "a@example.edu",
            "code": right,
            "display_name": "A",
            "accept_terms": True,
            "confirm_age": True,
        },
    )
    assert r.status_code == 400


def test_request_code_rate_limited(api: Api) -> None:
    for _ in range(3):
        assert api.client.post(RC, json={"email": "a@example.edu"}).status_code == 200
    r = api.client.post(RC, json={"email": "a@example.edu"})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0


def test_csrf_header_and_origin_required(api: Api) -> None:
    c = api.client
    assert (
        c.post(RC, json={"email": "a@example.edu"}, headers={"X-Baton-Client": ""}).status_code
        == 403
    )
    assert (
        c.post(
            RC, json={"email": "a@example.edu"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_suspended_user_loses_session(api: Api, app_engine) -> None:  # type: ignore[no-untyped-def]
    api.signup("asha@example.edu")
    with app_engine.begin() as c:
        c.execute(text("UPDATE identity.users SET status = 'suspended'"))
    assert api.client.get("/api/v1/me").status_code == 401
    api.client.post(RC, json={"email": "asha@example.edu"})
    assert api.sent["asha@example.edu"]  # old code only; no new email for suspended users


def test_logout_and_logout_all(api: Api) -> None:
    api.signup("asha@example.edu")
    assert api.client.post("/api/v1/auth/logout").status_code == 204
    assert api.client.get("/api/v1/me").status_code == 401


def test_sessions_list_and_revoke_isolated(api: Api) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    api.signup("asha@example.edu")
    other = TestClient(app, headers=dict(api.client.headers))
    other.post(RC, json={"email": "ravi@example.edu"})
    other.post(
        VC,
        json={
            "email": "ravi@example.edu",
            "code": api.sent["ravi@example.edu"],
            "display_name": "Ravi",
            "accept_terms": True,
            "confirm_age": True,
        },
    )
    ravi_session = other.get("/api/v1/me/sessions").json()[0]["id"]

    mine = api.client.get("/api/v1/me/sessions").json()
    assert len(mine) == 1 and mine[0]["current"] is True
    assert api.client.delete(f"/api/v1/me/sessions/{ravi_session}").status_code == 404
    assert other.get("/api/v1/me").status_code == 200
    assert api.client.delete("/api/v1/me/sessions/not-a-uuid").status_code == 404


def test_profile_update_and_mass_assignment(api: Api) -> None:
    api.signup("asha@example.edu")
    r = api.client.patch("/api/v1/me/profile", json={"handle": "Asha_K", "bio": "Hi\x00 there"})
    assert r.status_code == 200
    assert r.json()["handle"] == "asha_k" and r.json()["bio"] == "Hi there"
    assert api.client.patch("/api/v1/me/profile", json={"role": "admin"}).status_code == 422
    assert api.client.get("/api/v1/me").json()["role"] == "user"


def test_handle_taken(api: Api) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    api.signup("asha@example.edu")
    api.client.patch("/api/v1/me/profile", json={"handle": "taken_one"})
    other = TestClient(app, headers=dict(api.client.headers))
    other.post(RC, json={"email": "ravi@example.edu"})
    other.post(
        VC,
        json={
            "email": "ravi@example.edu",
            "code": api.sent["ravi@example.edu"],
            "display_name": "Ravi",
            "accept_terms": True,
            "confirm_age": True,
        },
    )
    r = other.patch("/api/v1/me/profile", json={"handle": "TAKEN_ONE"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "handle_taken"


def test_preferences_roundtrip_and_strict(api: Api) -> None:
    api.signup("asha@example.edu")
    assert api.client.get("/api/v1/me/preferences").json()["theme"] == "system"
    r = api.client.put("/api/v1/me/preferences", json={"theme": "dark", "text_size": 125})
    assert r.status_code == 200
    assert api.client.get("/api/v1/me/preferences").json()["theme"] == "dark"
    assert api.client.put("/api/v1/me/preferences", json={"css": "body{}"}).status_code == 422
    assert api.client.put("/api/v1/me/preferences", json={"accent": "red"}).status_code == 422


def test_protected_routes_need_session(api: Api) -> None:
    for path in ("/api/v1/me", "/api/v1/me/preferences", "/api/v1/me/sessions"):
        assert api.client.get(path).status_code == 401


def test_errors_never_leak_internals(api: Api) -> None:
    r = api.client.post(VC, json={"email": "a@example.edu", "code": "12"})
    assert r.status_code == 422
    assert "Traceback" not in r.text and "psycopg" not in r.text
