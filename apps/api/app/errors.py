import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("baton")

_DEFAULT_MESSAGES = {
    400: "That request didn't look right.",
    401: "Please sign in to continue.",
    403: "You don't have access to that.",
    404: "We couldn't find that.",
    405: "That action isn't allowed here.",
    409: "That can't be done right now.",
    413: "That's too large.",
    429: "Too many tries. Please wait a moment.",
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields
        self.headers = headers


def _body(request: Request, code: str, message: str, fields: dict[str, str] | None) -> Any:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    error["request_id"] = getattr(request.state, "request_id", None)
    return {"error": error}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            _body(request, exc.code, exc.message, exc.fields), exc.status, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        if any(err["loc"][:1] == ("path",) for err in exc.errors()):
            # Malformed ids look the same as missing ones (spec 7.4).
            return JSONResponse(_body(request, "not_found", _DEFAULT_MESSAGES[404], None), 404)
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            fields[".".join(loc) or "request"] = err["msg"]
        body = _body(request, "validation_failed", "Please fix the highlighted fields.", fields)
        return JSONResponse(body, 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _DEFAULT_MESSAGES.get(exc.status_code, "Something went wrong.")
        code = "not_found" if exc.status_code == 404 else f"http_{exc.status_code}"
        return JSONResponse(_body(request, code, message, None), exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", extra={"request_id": request.state.request_id})
        body = _body(request, "internal_error", "Something went wrong. Please try again.", None)
        return JSONResponse(body, 500)
