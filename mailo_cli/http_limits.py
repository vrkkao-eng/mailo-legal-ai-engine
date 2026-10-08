"""Bound request content before JSON parsing or domain work."""

from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mailo_cli.settings import ApiSettings


class RequestBodyLimitMiddleware:
    """Buffer at most the configured body limit, including chunked requests.

    The outer API middleware applies the request deadline and response metadata.
    The ASGI server owns HTTP framing and the size of each received frame.
    """

    def __init__(self, app: ASGIApp, settings: Callable[[], ApiSettings]):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self.settings().max_request_bytes
        lengths = [value for name, value in scope["headers"] if name == b"content-length"]
        declared_length: int | None = None
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                await self._reject(scope, receive, send, 400, "Invalid Content-Length")
                return
            # Compare digits first; arbitrarily long declarations need no int conversion.
            digits = lengths[0].lstrip(b"0") or b"0"
            maximum = str(limit).encode("ascii")
            if len(digits) > len(maximum) or (len(digits) == len(maximum) and digits > maximum):
                await self._reject(scope, receive, send, 413,
                                   "Request body exceeds configured size limit")
                return
            declared_length = int(digits)

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                # The outer BaseHTTPMiddleware requires a response start even
                # when the transport is gone. Uvicorn will discard the send;
                # this lets the outer layer record the cancellation cleanly.
                await self._reject(scope, receive, send, 499, "Client disconnected")
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                await self._reject(scope, receive, send, 413,
                                   "Request body exceeds configured size limit")
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        if declared_length is not None and declared_length != len(body):
            await self._reject(scope, receive, send, 400,
                               "Request body does not match Content-Length")
            return

        payload = bytes(body)
        del body
        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": payload, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send,
                      status: int, detail: str) -> None:
        await JSONResponse(status_code=status, content={"detail": detail})(scope, receive, send)
