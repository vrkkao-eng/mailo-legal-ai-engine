# Technical reviewer evidence map

This page is a navigation aid for technical review. It does not add claims beyond the implementation and evaluation artifacts already in this repository.

| Reviewer question | Short answer | Evidence to inspect |
| --- | --- | --- |
| **Why is this not just an LLM wrapper?** | Regulatory state transitions, supported applicability gates, evidence gaps, routing, persistence and audit semantics are deterministic application logic. The optional LLM loop is constrained to structuring supplied material. | [README](../README.md), [architecture boundaries](architecture-boundaries.md), tests under `tests/` |
| **Why not let the LLM decide applicability or compliance?** | Those decisions require traceable predicates, explicit abstention and reproducible review. The engine therefore keeps supported gates deterministic and routes unresolved facts to `REVIEW_REQUIRED`/human review rather than converting model confidence into a legal verdict. | [compliance workflow](compliance-workflow.md), [focused human review](human-review.md), applicability benchmark |
| **Is SHACL conformance the same as legal correctness?** | No. Conformance is relative to a selected shapes release and supplied data. The API records the selected profile/hash and explicitly does not present conformance as a legal-compliance determination. | README “HTTP service” / external-shapes manifest; canonical constraints live in MAILO ontology |
| **Is this production-ready?** | No. It is an engineering prototype with packaging, persistence, API, Docker and operational controls. Authentication/RBAC, external telemetry, HA/PostgreSQL, rate limiting and production deployment hardening remain outside the implemented scope. | README “Implemented now vs next engineering increment” and “HTTP service” |
| **What proves it is maintainable rather than a demo script?** | CI runs lint, typed-core checks, a coverage threshold, Python 3.11–3.13 tests, example validation, wheel build/clean-install smoke testing and Docker Compose health/persistence checks. | [CI workflow](../.github/workflows/tests.yml), `pyproject.toml` |
| **How is failure handled?** | Durable runs retain explicit failure codes, retryability, ordered workflow-step events and audit/review state. Operational reports distinguish completed, failed and replayed runs. | [operational evaluation](operational-evaluation.md), workflow persistence/observability docs |
| **Are the evaluation numbers legal-accuracy claims?** | No. Operational metrics measure workflow execution; legal accuracy, evidence sufficiency and human decision quality are explicitly outside those metrics. | [operational evaluation](operational-evaluation.md), benchmark docs |
| **Why separate the ontology and engine?** | Canonical legal knowledge/versioned SHACL belongs to the ontology; review state, API metadata, workflow timestamps and persistence belong to the application. This prevents application state from contaminating the legal knowledge model. | [architecture boundaries](architecture-boundaries.md) |

## Design position

The engineering position is intentionally conservative:

```text
LLM-assisted structuring
        ↓
reviewed/versioned inputs
        ↓
deterministic applicability + workflow logic
        ↓
explicit abstention / focused human review
        ↓
durable audit evidence
```

This is not a claim that legal interpretation can be made deterministic. The deterministic boundary covers the predicates and workflow semantics the prototype explicitly supports; interpretive uncertainty is surfaced rather than silently collapsed.

## Suggested verification path

A reviewer who has five minutes can verify the repository in this order:

1. inspect the architecture and implemented-vs-roadmap table in the README;
2. inspect `.github/workflows/tests.yml` and `pyproject.toml`;
3. run `mailo workflow-demo` or the Docker Compose operator demo;
4. inspect one benchmark/evaluation document and its corresponding tests;
5. inspect the ontology/engine ownership boundary.

