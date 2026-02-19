"""Request ID middleware — generates a unique ID per request for log correlation.

Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid buffering
StreamingResponse, which is needed for the SSE endpoint.
"""

import uuid
from contextvars import ContextVar

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdMiddleware:
    """Attach an 8-char request ID to every request/response cycle."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = uuid.uuid4().hex[:8]
        request_id_var.set(rid)
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_rid(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", rid)
            await send(message)

        await self.app(scope, receive, send_with_rid)
