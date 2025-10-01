"""Security helpers for the Remote MCP server."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response


class SharedSecretMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing a shared secret header on requests."""

    def __init__(self, app: FastAPI, secret: str) -> None:
        super().__init__(app)
        if not secret:
            raise ValueError("Shared secret must be configured")
        self._secret = secret

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == "/mcp/health":
            return await call_next(request)

        provided = request.headers.get("x-mcp-secret")
        if not provided or provided != self._secret:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return await call_next(request)


def apply_security(app: FastAPI, secret: str) -> None:
    """Configure middleware enforcing the shared secret and CORS defaults."""

    middleware = cast(Any, SharedSecretMiddleware)
    app.add_middleware(middleware, secret=secret)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST"],
        allow_headers=["*"],
    )
