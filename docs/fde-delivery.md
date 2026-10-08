# FDE delivery: durable FRIA workflow acceptance

This is a local, synthetic acceptance contract for a reviewer or integration
engineer. The user supplies a reviewed regulatory-change snapshot, receives a
durable workflow run ID, and uses that ID to inspect focused review and audit
state after a service restart. It addresses the operational pain of retrying a
request without knowing whether a prior attempt already created work.

## 30-minute reviewer walkthrough

Prerequisites: Docker Engine with Compose, Python 3.11 or newer, and an unused
local loopback port. No cloud account, LLM key, private data, or pip install is
required for the acceptance driver. From the repository root:

```bash
python tools/durable_acceptance.py --report acceptance-report.json
```

The driver chooses a free loopback port, creates a unique `mailo-accept-*`
Compose project, builds the current image, and sends the bundled synthetic
fixture `tools/fixtures/workflow_lifecycle.json` through real HTTP. It creates a
run, repeats the same request with the same `Idempotency-Key`, checks a changed
request with that key returns 409, and reads the review queue and case trace.
It also creates a domain-validation failure that is inspectable by run ID.
Then it stops and replaces the container while preserving the named volume,
reads both runs and operator views, repeats the original key, and exports a
JSON report. The unique test project and its synthetic volume are removed after
the check; the image and report remain. On failure, the report says `failed`
and includes the project name and cleanup outcome.

Preflight failures (including an unavailable port, unreadable fixture or Git
metadata) replace an earlier report at the same path with fresh failure evidence.
HTTP protocol errors are also recorded as failures. Cleanup's volume inspection
has a 30-second timeout; if cleanup cannot finish, the report records
`cleanup: failed` and `cleanup_error`. Use the reported project name to inspect
any remaining test resources before attempting project-scoped cleanup.

The report records the Git commit, whether its working tree was dirty, a source
tree hash, fixture SHA-256, Python/runtime package versions, image ID, executed
commands, request status/latency and request ID, before/after snapshots, run
identities, review/audit identities, container IDs and volume identity. Its
latency values are observations from this one local run, not capacity claims.

## Success and integration contract

The fixture should create one completed run with two focused reviews and two
`review_created` audit events. The same key and body must return HTTP 200 with
the same run ID and no extra review/audit/step records; a changed body using
that key must return HTTP 409. A deliberately inconsistent control mapping
must return HTTP 400 with a failed run ID that can be fetched. After container
replacement, both run snapshots, queue, case trace and operational report must
match the prior read, and another replay must remain stable.

Integration endpoints are `POST /workflow/runs` with a caller-generated
`Idempotency-Key`, `GET /workflow/runs/{run_id}`,
`GET /operator/api/reviews`, `GET /operator/api/cases/{run_id}` and
`GET /workflow/operations/report`. The caller supplies a reviewed change,
obligations, mappings, controls and evidence. `reviewer_role` in the workflow
is business data, not proof of caller identity. A client should retain its
idempotency key and run ID for retry and reconciliation. See
[workflow persistence](workflow-persistence.md) and
[operator surface](operator-surface.md) for field-level details.

## Recovery and limits

For a real deployment, preserve the SQLite database and any WAL/journal files
on a writable persistent volume, and back them up while the service is safely
stopped or through a consistent database backup. The acceptance driver does not
operate on a user's existing volume. If a root-owned legacy volume needs a UID
change, follow [runtime operations](runtime-operations.md) after confirming the
exact target and backup. A failed run remains inspectable; resending the same
key does not create a fresh run. For a corrected request, use a new key.

This exercise does not verify legal correctness, real customer adoption,
authentication, multi-tenant safety, cloud recovery, HA, or a real provider.
The reviewer walkthrough is a repeatable acceptance procedure; completion by
an independent reviewer should be recorded separately rather than assumed.
