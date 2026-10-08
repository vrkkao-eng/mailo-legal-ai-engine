"""Exercise raw ASGI frames; TestClient normally supplies Content-Length."""

import asyncio
import json

import pytest

import mailo_cli.api as api
from mailo_cli.settings import ApiSettings


def graph_body():
    return json.dumps({"findings": [{
        "category": "technology",
        "title": "Synthetic",
        "content": "Bounded source text",
        "source_url": "https://example.org/source",
    }]}).encode()


async def raw_request(monkeypatch, chunks, *, limit, headers=(), path="/graph",
                      method="POST", delay=0, timeout=30, disconnect=False):
    monkeypatch.setattr(api, "_SETTINGS", ApiSettings(
        max_request_bytes=limit, request_timeout_seconds=timeout,
    ))
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": [(b"content-type", b"application/json"), *headers],
        "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 8000),
    }
    messages = []
    received = 0

    async def receive():
        nonlocal received
        if received < len(chunks):
            if delay:
                await asyncio.sleep(delay)
            chunk = chunks[received]
            received += 1
            return {
                "type": "http.request", "body": chunk,
                "more_body": received < len(chunks) or disconnect,
            }
        if disconnect:
            return {"type": "http.disconnect"}
        await asyncio.Event().wait()

    async def send(message):
        messages.append(message)

    await asyncio.wait_for(api.app(scope, receive, send), timeout=5)
    start = next(item for item in messages if item["type"] == "http.response.start")
    content = b"".join(
        item.get("body", b"") for item in messages if item["type"] == "http.response.body"
    )
    return start["status"], dict(start["headers"]), json.loads(content), received


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [(), ((b"content-length", b"1"),)])
async def test_streamed_oversize_stops_before_processing_or_reading_tail(monkeypatch, headers):
    calls = []

    def unexpected_export(*args):
        calls.append(args)
        raise AssertionError("Oversized body reached application logic")

    monkeypatch.setattr(api, "export_findings", unexpected_export)
    body = graph_body()
    status, response_headers, content, reads = await raw_request(
        monkeypatch, [body[:16], body[16:64], body[64:]], limit=32, headers=headers,
    )
    assert status == 413
    assert "size limit" in content["detail"]
    assert response_headers[b"x-request-id"]
    assert response_headers[b"x-content-type-options"] == b"nosniff"
    assert reads == 2
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("extra_bytes", [0, 1])
async def test_streamed_body_at_or_below_limit_preserves_graph(monkeypatch, extra_bytes):
    body = graph_body()
    status, headers, content, reads = await raw_request(
        monkeypatch, [body[:7], b"", body[7:]], limit=len(body) + extra_bytes,
    )
    assert status == 200
    assert content["findings"] == 1
    assert "Bounded source text" in content["turtle"]
    assert headers[b"x-request-id"]
    assert reads == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [b"", b"-1", b"+1", b"abc", b"1.5", b" 1", b"1,1"])
async def test_invalid_length_rejected_without_reading_body(monkeypatch, value):
    status, headers, content, reads = await raw_request(
        monkeypatch, [graph_body()], limit=1024, headers=((b"content-length", value),),
    )
    assert status == 400
    assert content["detail"] == "Invalid Content-Length"
    assert headers[b"x-request-id"]
    assert reads == 0


@pytest.mark.asyncio
async def test_declared_oversize_rejected_without_reading_body(monkeypatch):
    status, headers, _, reads = await raw_request(
        monkeypatch, [graph_body()], limit=32,
        headers=((b"content-length", b"9" * 5000),),
    )
    assert status == 413
    assert headers[b"x-request-id"]
    assert reads == 0


@pytest.mark.asyncio
async def test_duplicate_length_rejected_without_reading_body(monkeypatch):
    status, headers, _, reads = await raw_request(
        monkeypatch, [graph_body()], limit=1024,
        headers=((b"content-length", b"1"), (b"content-length", b"2")),
    )
    assert status == 400
    assert headers[b"x-request-id"]
    assert reads == 0


@pytest.mark.asyncio
async def test_length_mismatch_rejected_before_processing(monkeypatch):
    body = graph_body()
    status, headers, content, _ = await raw_request(
        monkeypatch, [body], limit=1024, headers=((b"content-length", b"1"),),
    )
    assert status == 400
    assert content["detail"] == "Request body does not match Content-Length"
    assert headers[b"x-request-id"]


@pytest.mark.asyncio
async def test_one_byte_above_limit_is_rejected(monkeypatch):
    body = graph_body()
    status, _, _, _ = await raw_request(monkeypatch, [body], limit=len(body) - 1)
    assert status == 413


@pytest.mark.asyncio
async def test_limit_applies_when_endpoint_does_not_use_body(monkeypatch):
    status, _, _, _ = await raw_request(
        monkeypatch, [b"12345"], limit=4, path="/health", method="GET",
    )
    assert status == 413


@pytest.mark.asyncio
async def test_body_read_is_covered_by_request_deadline(monkeypatch):
    status, headers, content, reads = await raw_request(
        monkeypatch, [graph_body()], limit=1024, delay=2, timeout=1,
    )
    assert status == 504
    assert content["detail"] == "Request timed out"
    assert headers[b"x-request-id"]
    assert reads == 0


@pytest.mark.asyncio
async def test_middleware_passes_non_http_scope_through():
    from mailo_cli.http_limits import RequestBodyLimitMiddleware

    calls = []

    async def downstream(scope, receive, send):
        calls.append(scope["type"])

    async def unused():
        raise AssertionError("Non-HTTP scope read as a body")

    await RequestBodyLimitMiddleware(downstream, ApiSettings)(
        {"type": "lifespan"}, unused, unused,
    )
    assert calls == ["lifespan"]


@pytest.mark.asyncio
async def test_disconnect_during_upload_does_not_start_domain_work():
    from mailo_cli.http_limits import RequestBodyLimitMiddleware

    calls = []
    messages = iter([
        {"type": "http.request", "body": b"partial", "more_body": True},
        {"type": "http.disconnect"},
    ])

    async def downstream(*args):
        calls.append("downstream")

    async def receive():
        return next(messages)

    async def send(message):
        calls.append(message)

    await RequestBodyLimitMiddleware(downstream, ApiSettings)(
        {"type": "http", "headers": []}, receive, send,
    )
    assert [item["status"] for item in calls if item["type"] == "http.response.start"] == [499]


@pytest.mark.asyncio
async def test_disconnect_during_upload_is_recorded_by_full_stack(monkeypatch):
    calls = []
    access_events = []

    def unexpected_export(*args):
        calls.append(args)
        raise AssertionError("Disconnected upload reached domain work")

    monkeypatch.setattr(api, "export_findings", unexpected_export)
    monkeypatch.setattr(api._LOGGER, "info", lambda message: access_events.append(json.loads(message)))
    status, headers, content, reads = await raw_request(
        monkeypatch, [b'{"findings":'], limit=1024, disconnect=True,
    )

    assert status == 499
    assert content["detail"] == "Client disconnected"
    assert headers[b"x-request-id"]
    assert reads == 1
    assert calls == []
    assert len(access_events) == 1
    assert access_events[0]["status"] == 499
    assert access_events[0]["request_id"] == headers[b"x-request-id"].decode()
