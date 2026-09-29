# v0.5.0 — Stateless RegAI workflow API

v0.5.0 turns the completed v0.4.x workflow contracts into an integration-facing
application service without pretending that persistence already exists.

## Service boundary

The API follows three layers:

```text
HTTP / Pydantic transport schemas
        ↓
stateless application service
        ↓
existing regulatory domain contracts
```

FastAPI handlers do not reimplement evidence-gap, impact-propagation, or review-
routing logic.

## Endpoints

### `POST /workflow/evaluate`

Accepts one reviewed regulatory change plus supplied organisation workflow data:

- reviewed obligations;
- reviewed obligation/control mappings;
- controls;
- evidence requirements;
- registered evidence records.

The response contains:

- evidence-gap candidates;
- regulatory-impact candidates;
- focused review routes;
- a compact workflow summary;
- `compliance_determination_produced = false`.

The endpoint is deterministic for the same validated request payload.

### `GET /workflow/demo`

Runs the bundled offline FRIA end-to-end scenario from v0.4.4 and returns the
scenario counts and workflow benchmark report.

It requires no API key, external database, or LLM provider.

## Error semantics

Transport validation failures use FastAPI/Pydantic validation responses.
Domain-integrity failures such as inconsistent reviewed mappings return HTTP 400.

Unexpected processing failures remain HTTP 500 without leaking internal
exception details.

Every HTTP response continues to receive the existing `X-Request-ID` header and
structured access-log entry.

## Stateless by design

v0.5.0 does not persist:

- review cases;
- human responses;
- audit events;
- controls;
- evidence records;
- workflow run state.

A successful response therefore means only that the supplied snapshot was
evaluated. It does not create a durable case or audit record.

Persistence is intentionally deferred to v0.5.1 so that transactional storage
semantics are introduced explicitly rather than hidden inside the API adapter.

## Deferred

v0.5.0 does not add:

- PostgreSQL/SQLite persistence;
- authentication or RBAC;
- external regulatory feeds;
- notifications or task queues;
- Neo4j/vector databases;
- remediation execution;
- production deployment claims;
- automatic legal-compliance decisions.
