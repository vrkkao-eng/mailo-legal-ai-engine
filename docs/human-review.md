# v0.4.3 — Focused human review, routing and audit trail

v0.4.3 converts selected v0.4.2 workflow candidates into focused human-review
questions without exposing an AI recommendation or compliance verdict.

## Anti-rubber-stamping design

The review contract deliberately avoids generic approval actions.

```text
Candidate
    -> ReviewRoute
    -> focused ReviewQuestion
    -> HumanResponse
    -> append-only AuditEvent
    -> resolve / continue / escalate
```

There is no `APPROVE_AI`, `REJECT_AI`, `COMPLIANT`, or
`NON_COMPLIANT` answer.

Human responses are limited to `YES`, `NO`, and `UNKNOWN` against a
specific question. `UNKNOWN` is a valid safe response and cannot resolve a
review case.

## Cognitive-burden controls

Routing is selective:

- optional evidence gaps default to `LOG_ONLY`;
- mandatory evidence gaps create a focused AI-governance question;
- regulatory-impact candidates route to a Legal reviewer;
- candidate context is referenced by identifiers rather than duplicated into a
  large review payload.

This release therefore does not require a human to approve every machine
candidate.

## Review-state semantics

`ReviewStatus` describes workflow state only:

- `OPEN`
- `IN_REVIEW`
- `RESOLVED`
- `ESCALATED`

`RESOLVED` means that the review case was handled. It does not mean that a
legal, regulatory, control, evidence, or compliance issue was resolved.

A resolved case requires:

- at least one human response;
- a non-`UNKNOWN` latest answer; and
- a `REVIEW_CLOSED` audit event.

An escalated case requires explicit escalation details and an `ESCALATED`
audit event.

## Audit trail

Audit events are append-only and chronological. Event IDs must be unique and
every event must reference the same review case.

Supported events:

- `REVIEW_CREATED`
- `REVIEW_STARTED`
- `RESPONSE_RECORDED`
- `INFORMATION_REQUESTED`
- `ESCALATED`
- `REVIEW_CLOSED`

The audit trail records what happened in the workflow. It does not certify that
the underlying legal interpretation was correct.

## Deferred

v0.4.3 does not add:

- reviewer-performance metrics;
- benchmark scoring;
- cognitive-load measurement;
- UI or task queues;
- SLA/deadline automation;
- notifications;
- remediation execution;
- automatic legal conclusions; or
- LLM-generated reviewer answers.

These remain outside v0.4.3. Workflow evaluation belongs to v0.4.4.
