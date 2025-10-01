"""Security helpers for the Remote MCP server."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class SharedSecretMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing a shared secret header on requests."""

    def __init__(self, app: ASGIApp, secret: str) -> None:
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


def build_security_middleware(secret: str) -> list[Middleware]:
    """Create the middleware enforcing the shared secret and CORS defaults."""

    if not secret:
        raise ValueError("Shared secret must be configured")

    return [
        Middleware(SharedSecretMiddleware, secret=secret),
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["POST"],
            allow_headers=["*"],
        ),
    ]
