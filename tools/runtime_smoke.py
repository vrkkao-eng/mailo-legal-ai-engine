"""Black-box local HTTP checks; use only the bundled synthetic input."""

import argparse
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit


def check_runtime(url: str, limit: int) -> dict:
    target = urlsplit(url)
    if (target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost", "::1"}
            or target.username or target.password or target.query or target.fragment
            or target.path not in {"", "/"}):
        raise ValueError("Use a loopback HTTP origin, without credentials or a path")
    if not 1 <= limit <= 10_485_760:
        raise ValueError("Body limit must be between 1 and 10485760")
    results = []

    def request(name, method, path, *, body=None, headers=None, chunked=False, expected=200):
        connection = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers or {},
                               encode_chunked=chunked)
            response = connection.getresponse()
            content = json.loads(response.read())
            if response.status != expected:
                raise RuntimeError(f"{name}: expected {expected}, got {response.status}")
            for header in ("X-Request-ID", "X-Content-Type-Options", "X-Frame-Options"):
                if not response.getheader(header):
                    raise RuntimeError(f"{name}: missing {header}")
            results.append({"check": name, "status": response.status, "passed": True})
            return content
        finally:
            connection.close()

    if request("health", "GET", "/health") != {"status": "ok"}:
        raise RuntimeError("Unexpected health result")
    if request("ready", "GET", "/ready") != {"status": "ready"}:
        raise RuntimeError("Unexpected readiness result")
    if not isinstance(request("storage_read", "GET", "/operator/api/changes"), list):
        raise RuntimeError("Unexpected operator read result")

    body = json.dumps({"findings": [{
        "category": "technology", "title": "Synthetic",
        "content": "Local smoke text", "source_url": "https://example.org/source",
    }]}).encode()
    if len(body) > limit:
        raise ValueError(f"Synthetic graph smoke needs a limit of at least {len(body)} bytes")
    graph = request("chunked_graph", "POST", "/graph", body=[body[:8], body[8:]],
                    headers={"Content-Type": "application/json"}, chunked=True)
    if graph.get("findings") != 1 or "Local smoke text" not in graph.get("turtle", ""):
        raise RuntimeError("Chunked graph content was not preserved")

    def excess_chunks():
        remaining = limit + 1
        while remaining:
            size = min(remaining, 65_536)
            yield b"x" * size
            remaining -= size

    excess = request("chunked_oversize", "POST", "/graph", body=excess_chunks(),
                     headers={"Content-Type": "application/json"}, chunked=True, expected=413)
    if "size limit" not in excess.get("detail", ""):
        raise RuntimeError("Expected body size rejection")
    request("declared_oversize", "POST", "/graph", body=b"",
            headers={"Content-Length": str(limit + 1)}, expected=413)
    request("health_after_rejection", "GET", "/health")
    return {
        "status": "passed", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "url": url, "max_request_bytes": limit, "checks": results,
        "scope": "Local HTTP and storage initialization; not durable restart or legal evaluation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--max-request-bytes", type=int, default=1_048_576)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = check_runtime(args.url, args.max_request_bytes)
    except (ValueError, RuntimeError, OSError, http.client.HTTPException) as exc:
        report = {"status": "failed", "error": str(exc)}
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
