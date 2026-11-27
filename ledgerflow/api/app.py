"""FastAPI application factory: error envelope, request IDs and health endpoints.

Auth, tenancy, workbooks and runs arrive in later milestones. Health endpoints
deliberately expose no versions, paths, sandbox or model details (API_CONTRACT).
"""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ledgerflow.config import Settings
from ledgerflow.persistence.db import migrate, open_pool

log = logging.getLogger("ledgerflow.api")

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class ApiError(Exception):
    """An error with a stable machine-readable code, per the API error envelope."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE",
    429: "RATE_LIMITED",
    503: "UNAVAILABLE",
}


def _envelope(
    request: Request,
    status: int,
    code: str,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "request_id": request.state.request_id,
            "details": details or {},
        }
    }
    return JSONResponse(body, status_code=status)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # The pool closes on exit; migrations run once per process start.
        with open_pool(settings.database_url) as pool:
            with pool.connection() as conn:
                migrate(conn)
            app.state.db = pool
            app.state.settings = settings
            yield

    app = FastAPI(
        title="LedgerFlow API",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("X-Request-Id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else f"req_{secrets.token_hex(8)}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return _envelope(
            request,
            exc.status,
            exc.code,
            exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "ERROR")
        message = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ").lower()
        return _envelope(request, exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field locations only: never echo submitted values back.
        fields = ["/".join(str(part) for part in err["loc"]) for err in exc.errors()]
        return _envelope(
            request,
            400,
            "BAD_REQUEST",
            "request does not match the contract",
            details={"fields": fields[:20]},
        )

    @app.exception_handler(psycopg.Error)
    async def database_error_handler(request: Request, exc: psycopg.Error) -> JSONResponse:
        # Log the detail server-side; the client gets a retryable generic error.
        log.error("database error on %s: %s", request.url.path, type(exc).__name__)
        return _envelope(request, 503, "UNAVAILABLE", "temporary storage error", retryable=True)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s", request.url.path)
        return _envelope(request, 500, "INTERNAL", "internal error")

    @app.get("/api/v1/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health/ready", tags=["health"])
    def ready(request: Request) -> JSONResponse:
        # Sync on purpose: pool checkout blocks, so FastAPI runs it in a thread.
        try:
            with request.app.state.db.connection() as conn:
                conn.execute("SELECT 1")
        except psycopg.Error:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ok"})

    return app
