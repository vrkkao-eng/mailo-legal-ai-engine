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
| v0.5.x | Can the workflow be evaluated and demonstrated end to end? | Unified eval harness, hybrid retrieval experiments, minimal product UI, end-to-end scenario |

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
Represent evidence requirements and evidence records without treating document
presence as proof of compliance.

### v0.4.2 — gap and regulatory-impact analysis
Propagate reviewed obligation/control relationships into evidence-gap and
regulatory-change review candidates.

### v0.4.3 — human review and audit trail
Add explicit review decisions, reasons, timestamps, and escalation state while
keeping machine suggestions separate from human determinations.

### v0.4.4 — workflow evaluation and end-to-end scenario
Evaluate mapping completeness, evidence-gap handling, review routing, and audit
traceability on a fixed reviewed scenario.

## Design principle

A regulatory change record means that a selected text changed between two
reviewed versions. It does not by itself mean that an obligation applies to a
specific actor, system, or date. Applicability belongs to the v0.3 line.
