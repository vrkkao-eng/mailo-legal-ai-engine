# v0.5.1 — Transactional workflow persistence

v0.5.1 adds a durable operational state layer beneath the v0.5.0 workflow API.

## Storage model

The current implementation uses Python's built-in SQLite driver and creates the
following relational tables:

- workflow_runs
- evidence_records
- review_cases
- human_responses
- escalations
- audit_events

The persistence layer is separate from the legal/ontology layer. It stores
workflow state and evidence metadata; it does not become a canonical legal
knowledge source.

## Durable workflow runs

POST /workflow/runs evaluates the same typed workflow payload accepted by
POST /workflow/evaluate and then persists the resulting snapshot atomically.

Each durable run has:

- workflow run ID;
- caller-provided Idempotency-Key;
- canonical request SHA-256;
- regulatory change ID;
- created timestamp;
- persisted request snapshot;
- persisted workflow result.

Human-review routes create OPEN review cases and REVIEW_CREATED audit events in
the same transaction.

## Idempotency

The Idempotency-Key header is required for durable creation.

- same key + same canonical request -> original workflow run, HTTP 200;
- new key -> new durable run, HTTP 201;
- same key + different request -> HTTP 409.

This prevents duplicate review cases and audit records when callers retry a
request after a network or client failure.

## Human responses

POST /workflow/reviews/{review_id}/responses persists a focused human response.

- YES or NO -> RESOLVED plus REVIEW_CLOSED audit event;
- UNKNOWN -> requires an escalation target and becomes ESCALATED;
- reviewer role must match the assigned review role.

Responses, state transitions, escalation records, and audit events are committed
atomically.

## Retrieval

GET /workflow/runs/{run_id} returns the persisted result together with current
review cases and audit events.

Missing runs return HTTP 404.

## Configuration

Set MAILO_WORKFLOW_DB to choose the SQLite file path.

Default:

    artifacts/workflow.db

The implementation creates parent directories when necessary.

## Scope boundary

v0.5.1 implements SQLite transactional persistence only. The repository boundary
is intentionally isolated from domain evaluation so a later relational backend
can replace the storage implementation without moving workflow state into MAILO
ontology objects.

v0.5.1 does not claim:

- PostgreSQL support;
- database migrations across released schemas;
- distributed locking;
- multi-tenant isolation;
- authentication/RBAC;
- production HA;
- external regulatory feeds;
- graph/vector persistence.
