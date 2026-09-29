# RegAI roadmap

This roadmap extends the existing `mailo-legal-ai-engine` instead of creating a
parallel RegAI repository. The objective is to turn the existing engineering
foundation into an auditable regulatory-AI application while keeping legal
knowledge, application workflow, and reasoning-system research separate.

## Version sequence

| Version | Primary question | Scope |
| --- | --- | --- |
| v0.1.x | Can the project expose a reliable legal-AI engineering pipeline? | CLI/API, RDF/JSON-LD, reviewed SPARQL, SHACL, provenance, tests, CI, Docker, exploratory retrieval baseline |
| **v0.2.x** | What changed in the regulation? | Version-aware regulatory sources, reviewed change fixtures, deterministic structural diff, change benchmark |
| v0.3.x | What does the change mean for a described system? | Obligation representation, applicability, candidate extraction, abstention/evaluation |
| v0.4.x | What should an organisation review or evidence? | Control mapping, evidence records, human review, impact propagation |
| v0.5.x | Can the workflow operate as an integration-ready application service? | Workflow API, persistence, observability, operational evaluation |

## v0.2.0 scope

v0.2.0 introduces the application-layer vocabulary needed for later regulatory
change detection:

- `RegulatorySource`
- `RegulatoryVersion`
- `Provision`
- `RegulatoryChange`
- `ChangeType`
- `SourceLocator`
- `RegulatoryChangeSet`

The first reviewed fixture records selected changes made to Regulation (EU)
2024/1689 by Regulation (EU) 2026/1744. It is a deterministic test fixture, not
an automated legal update feed.

### Deliberately out of scope

v0.2.0 does **not** add:

- automatic document diffing;
- LLM extraction;
- compliance determinations;
- applicability decisions;
- organisation controls or evidence;
- vector retrieval or Qdrant;
- a UI;
- code coupling to `adaptive-kg-reasoning`.

## v0.2.x planned increments

### v0.2.1 — deterministic structural diff
Normalise versioned texts into stable article/paragraph units and identify
added, deleted, text-changed and date-changed candidates without an LLM.

### v0.2.2 — reviewed change reconciliation
Reconcile deterministic structural candidates with reviewed source-aware change
records. Preserve unreviewed candidates explicitly, allow reviewed metadata to
refine supported types such as TEXT_CHANGED to DATE_CHANGED, and never promote
machine candidates into legal conclusions silently.

### v0.2.3 — reviewed change benchmark
Close the v0.2.x line with a named reviewed gold set and reproducible precision,
recall, F1, locator accuracy, exact type accuracy, and reviewed type coverage.
Seed-set scores are regression evidence only, not population-level performance.

## v0.3.x planned increments

### v0.3.0 — obligation representation
Define reviewed actor/action/object/modality obligation units, minimal system descriptions, and a three-state applicability contract with explicit REVIEW_REQUIRED abstention.

### v0.3.1 — change-to-obligation candidates
Link reviewed regulatory changes to candidate affected obligations while preserving provenance and human review.

### v0.3.2 — applicability engine
Evaluate supported factual gates against system descriptions. Missing or interpretively unresolved facts must route to REVIEW_REQUIRED rather than a forced binary result.

### v0.3.3 — obligation/applicability evaluation
Benchmark candidate extraction, supported applicability decisions, abstention appropriateness, and provenance completeness.

## v0.4.x planned increments

### v0.4.0 — reviewed obligation-to-control contracts
Introduce organisation-owned `Control` records and reviewed
`ObligationControlMapping` links. Control implementation state is operational
workflow data and is not a legal-compliance verdict.

### v0.4.1 — control evidence requirements
Represent reviewed evidence requirements and supplied evidence records with
URI/hash/timestamp/owner provenance. Validate record-to-requirement references
and evidence-type consistency without treating artefact presence as proof of
sufficiency or compliance.

### v0.4.2 — gap and regulatory-impact analysis
Identify reviewed evidence requirements with no registered records and propagate
reviewed regulatory changes through obligation-to-control mappings to downstream
evidence requirements. Outputs are review candidates only; they do not establish
evidence insufficiency, control failure, or legal non-compliance.

### v0.4.3 — focused human review, routing and audit trail
Route selected machine-generated candidates into focused human questions with
explicit YES/NO/UNKNOWN responses, role-based routing, append-only audit events,
and escalation. Optional evidence gaps may remain log-only. The review layer does
not expose AI approval/compliance verdicts and UNKNOWN cannot close a review.

### v0.4.4 — workflow evaluation and end-to-end scenario
Close the v0.4.x line with a deterministic fixed FRIA scenario, routing and
traceability benchmarks, audit/escalation integrity checks, UNKNOWN-safety
checks, and explicitly labelled workflow-burden proxies. These proxies are not
human cognitive-load measurements.

## v0.5.x planned increments

### v0.5.0 — stateless workflow API
Expose the completed v0.4.x regulatory workflow through typed HTTP transport
schemas and a stateless application-service layer. Support workflow evaluation
and an offline end-to-end demo without duplicating domain logic or claiming
persistence.

### v0.5.1 — transactional persistence
Add SQLite transactional persistence for durable workflow-run identifiers,
evidence metadata, focused review cases, human responses, escalations, and audit
events. Require idempotency keys for durable creation so retries do not duplicate
review work. The storage boundary remains separate from domain/legal semantics.

### v0.5.2 — observability and failure semantics
Reserve durable runs before evaluation, record ordered workflow-step events with
timings, expose stable failure codes/retryability, and keep failed runs
inspectable by workflow-run ID. Observability remains application-local; external
telemetry backends are deferred.

### v0.5.3 — operational evaluation
Evaluate persisted workflow completion/failure behaviour, failure taxonomy,
step-latency summaries, and deterministic replay consistency from canonical
request hashes. Add a minimal forward migration for existing SQLite workflow
databases. Engineering metrics are not legal-quality scores.

### v0.5.4 — minimal operator surface
Close the v0.5.x line with three read-only operator views: regulatory changes,
focused review queue, and auditable case trace. The UI is dependency-free and
local/demo-oriented; authentication, RBAC and production console security remain
explicitly out of scope.

## Design principle

A regulatory change record means that a selected text changed between two
reviewed versions. It does not by itself mean that an obligation applies to a
specific actor, system, or date. Applicability belongs to the v0.3 line.
