# Local runtime contract

The service is a single-host engineering prototype. Compose exposes it at
`127.0.0.1:8000`. It has no authentication or RBAC; the supplied reviewer role
is workflow data rather than verified caller identity.

## Install and reproduce

From the repository root:

```bash
python -m pip install -c constraints.txt ".[dev,research,service,retrieval]"
python -m pytest -q
ruff check mailo_cli tests
mypy mailo_cli/regulatory mailo_cli/workflow_api.py mailo_cli/http_limits.py
docker compose up --detach --build
python tools/runtime_smoke.py
```

`constraints.txt` pins versions for the declared extras, including transitive
runtime packages. Unused extras are not installed. The Docker builder resolves
the service extra with these constraints and produces wheels; the runtime stage
installs only from that local wheel set. No repository checkout is needed in the
runtime image. Build-isolation tooling is not locked by this constraints file,
so this is not a claim of bit-identical image builds or a hash-locked supply chain.

The Python base index is pinned to
`sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f`,
resolved on 2026-10-08 (linux/amd64 reports Python 3.12.15). Refresh base images
and constraints deliberately, then run the Python matrix, quality and container
checks. Digest/version pins require maintenance; they are not a vulnerability
scan.

The constraints were resolved against Python 3.11 Linux-compatible requirements
and include Windows-only colorama. Python 3.11–3.13 are configured in CI; a
configured matrix should not be described as a successful run before checks pass.

## HTTP body boundary

`MAILO_MAX_REQUEST_BYTES` defaults to 1,048,576 (maximum 10,485,760). An oversized
declared length is rejected without reading content. Content is accumulated only
while its actual byte count stays within the limit; a chunk that would exceed it
causes 413 before JSON parsing or domain work. Remaining chunks are not read by
the application. Exactly the limit is accepted subject to normal schema checks.

Absent Content-Length is supported, including chunked uploads. Empty, signed,
nondecimal or duplicate Content-Length headers cause 400; an in-limit declared
length that differs from the actual body also causes 400. Very large declarations
are compared as decimal digits before any integer conversion.

The outer request deadline includes body intake. Rejections retain the existing
request ID, browser-safety headers and JSON access log. Body bytes are bounded,
but total process memory also includes the ASGI frame, a temporary buffer copy,
parsed data and response work. HTTP wire framing and individual frame allocation
belong to the server. The controls do not sandbox SHACL/RDF CPU work.

The smoke checker uses real HTTP chunked requests to validate the configured
limit. If overriding the service limit, pass the same value through its
`--max-request-bytes` argument. It also checks health/readiness and exercises
workflow storage initialization with the operator read endpoint. Durable workflow
creation/replay/restart acceptance is available through
`python tools/durable_acceptance.py --report acceptance-report.json`; see
[FDE delivery and recovery](fde-delivery.md). The acceptance tool overrides the
Compose host port with an unused loopback port; normal Compose still defaults
to `127.0.0.1:8000`.

## Non-root storage

The runtime process uses UID/GID `10001:10001`. `/app` is only its working
directory; installed code is in site-packages. The default database is
`/data/workflow.db`, and the image owns `/data` as this user. A fresh Docker named
volume inherits these permissions. Graph exports use temporary directories.
The supplied `.env.example` leaves `MAILO_WORKFLOW_DB` unset, including when
copied to `.env`, so Compose continues to use `/data/workflow.db`. A relative
`artifacts/workflow.db` override is for direct local Python use, not this image.

Do not delete an existing volume to solve a permission error. For a volume created
by the previous root-running image:

1. Stop the service and preserve a backup of the entire workflow database set,
   including any journal/WAL files. A live file copy is not a verified backup.
2. Inspect the actual mounted volume or bind path and its ownership. Preserve the
   old image and backup for rollback.
3. Adjust only the intended `/data` directory and existing database/journal files
   to UID/GID 10001. On a managed Docker volume, a one-off container with
   `--user 0` can do this after the targets are confirmed. Do not recursively
   change an unrelated host directory or assume a bind mount is disposable.
4. Start the new image and verify `/operator/api/changes` plus the existing
   workflow records. An empty result alone does not prove successful migration.

Runtime migration does not change the application schema. Compose preserves its
named volume unless explicitly asked to remove it. CI creates and cleans its own
disposable volume; those cleanup commands are not recovery instructions for a
user's volume.

The Docker healthcheck checks `/health`. `/ready` verifies registered shapes;
successful durable operations are needed to establish usable storage. Neither
endpoint asserts HA or production capacity.
