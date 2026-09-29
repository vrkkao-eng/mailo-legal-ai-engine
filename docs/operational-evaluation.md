# v0.5.3 — Operational evaluation

v0.5.3 evaluates persisted workflow execution as an engineering system.

## Report

GET /workflow/operations/report summarizes the current workflow database:

- run count;
- completed / failed / running counts;
- completion rate;
- retryable and non-retryable failures;
- failure-code distribution;
- workflow-step event count;
- mean, p50 and p95 step duration;
- deterministic replay groups;
- replay consistency.

A replay group is formed when multiple durable runs have the same canonical
request SHA-256 but different durable identities. A group is consistent when
status, failure metadata and persisted workflow result match.

## What the metrics mean

These are operational engineering metrics. They do not measure legal accuracy,
evidence sufficiency, compliance quality, or human decision quality.

Latency numbers are observations from the current runtime and dataset. They are
not production capacity claims.

## Schema reliability

v0.5.3 also adds a minimal forward migration for SQLite workflow databases
created before v0.5.2. Missing workflow failure columns are added on repository
initialization, and the workflow_steps table is created if absent.

This is intentionally small-scope migration support, not a general migration
framework.
