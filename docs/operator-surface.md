# v0.5.4 — Minimal operator surface

v0.5.4 closes the v0.5.x applicationisation line with a small operator-facing
surface over the existing workflow API and SQLite persistence layer.

## Views

The local page at /operator contains three views.

### Regulatory Changes

Aggregates durable workflow runs by regulatory change and shows:

- change ID;
- run count;
- latest workflow status;
- failed-run count;
- latest workflow run ID.

### Review Queue

Lists persisted focused review cases with:

- review status;
- assigned reviewer role;
- subject type and subject ID;
- regulatory change;
- workflow run ID;
- escalation metadata when present.

### Case Trace

Shows one workflow run as an operational trace:

- regulatory change and run identity;
- workflow status and failure metadata;
- evaluate / persist / review-ready step events;
- focused review cases;
- append-only audit events;
- explicit compliance_determination_produced boundary.

## Read APIs

The UI consumes read-only endpoints:

- GET /operator/api/changes
- GET /operator/api/reviews
- GET /operator/api/cases/{run_id}

Workflow mutations remain on the existing /workflow endpoints.

## Implementation boundary

The operator surface uses server-hosted HTML plus dependency-free browser
JavaScript. It does not add a frontend framework or duplicate business logic.

The page is intended for local/demo portfolio use. It has no authentication,
RBAC, tenant isolation, CSRF model, or production admin-console security.
Do not expose it publicly without adding those controls.
