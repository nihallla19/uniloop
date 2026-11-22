import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import Connection

from app.db import get_conn
from app.modules.identity import service
from app.modules.identity.schemas import (
    Preferences,
    ProfilePatch,
    RequestCodeIn,
    VerifyCodeIn,
)
from app.security.rate_limit import client_ip
from app.security.sessions import CurrentUser, optional_user, require_user

router = APIRouter()


# Public


@router.post("/auth/request-code")
def request_code(
    body: RequestCodeIn, request: Request, conn: Connection = Depends(get_conn)
) -> dict[str, str]:
    service.request_code(conn, body.email, body.turnstile_token, client_ip(request))
    return {"message": service.GENERIC_CODE_MESSAGE}


@router.post("/auth/verify-code")
def verify_code(
    body: VerifyCodeIn,
    request: Request,
    response: Response,
    conn: Connection = Depends(get_conn),
    current: CurrentUser | None = Depends(optional_user),
) -> dict[str, bool]:
    ua = request.headers.get("user-agent", "")
    return service.verify_code(conn, body, client_ip(request), ua, response, current)


# User


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    conn: Connection = Depends(get_conn),
    user: CurrentUser = Depends(require_user),
) -> None:
    service.logout(conn, user, response)


@router.post("/auth/logout-all", status_code=204)
def logout_all(
    response: Response,
    conn: Connection = Depends(get_conn),
    user: CurrentUser = Depends(require_user),
) -> None:
    service.logout_all(conn, user, response)


@router.get("/me")
def me(
    conn: Connection = Depends(get_conn), user: CurrentUser = Depends(require_user)
) -> dict[str, Any]:
    return service.get_me(conn, user)


@router.patch("/me/profile")
def update_profile(
    body: ProfilePatch,
    conn: Connection = Depends(get_conn),
    user: CurrentUser = Depends(require_user),
) -> dict[str, Any]:
    return service.update_profile(conn, user, body)


@router.get("/me/preferences")
def get_preferences(
    conn: Connection = Depends(get_conn), user: CurrentUser = Depends(require_user)
) -> Preferences:
    return service.get_preferences(conn, user)


@router.put("/me/preferences")
def put_preferences(
    body: Preferences,
    conn: Connection = Depends(get_conn),
    user: CurrentUser = Depends(require_user),
) -> Preferences:
    return service.put_preferences(conn, user, body)


@router.get("/me/sessions")
def list_sessions(
    conn: Connection = Depends(get_conn), user: CurrentUser = Depends(require_user)
) -> list[dict[str, Any]]:
    return service.list_sessions(conn, user)


@router.delete("/me/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: uuid.UUID,
    conn: Connection = Depends(get_conn),
    user: CurrentUser = Depends(require_user),
) -> None:
    service.revoke_session(conn, user, session_id)
