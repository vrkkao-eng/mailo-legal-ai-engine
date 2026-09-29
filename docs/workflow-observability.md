# v0.5.2 — Workflow observability and failure semantics

v0.5.2 makes durable workflow execution inspectable at the application level.

## Observable execution

Durable workflow requests are reserved before evaluation starts. Each run then
records ordered operational step events:

- evaluate
- persist
- review_ready

Each event stores status, duration, detail, and optional error metadata.

## Failure taxonomy

The workflow exposes stable error codes:

- domain_validation_failed
- persistence_failed
- review_persistence_failed
- internal_error

Failure metadata includes:

- failed_step
- error_code
- retryable
- error_detail
- workflow_run_id

Domain validation failures are non-retryable. Persistence failures are marked
retryable.

## Inspectable failed runs

If evaluation fails after the run is reserved, the API returns an error payload
containing the workflow_run_id. Operators can then call:

    GET /workflow/runs/{run_id}

to inspect the failed snapshot and its step events.

## Idempotent replay

Replaying a completed request with the same Idempotency-Key returns the original
run and does not duplicate step events, review cases, or audit events.

## Scope

This release provides application-level observability. It does not add
Prometheus, OpenTelemetry exporters, external log aggregation, alerting, or
distributed tracing.
