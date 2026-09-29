# v0.4.0 — Obligation to Control contract

v0.4.0 starts the compliance-workflow layer. It turns a reviewed application-layer obligation into an organisation-owned control without changing canonical MAILO legal semantics.

## Authority boundary

- **MAILO ontology** owns canonical legal concepts, relations, source annotations and substantive legal constraints.
- **mailo-legal-ai-engine** owns organisation-facing workflow objects such as controls, owners and implementation state.
- A control status is **not** a legal-compliance verdict.
- v0.4.0 accepts only **reviewed** obligation-to-control mappings. Automated control generation is outside this release.

## Contract

A `Control` identifies the obligation it operationalises, its control type, organisation owner and implementation state. The default state is `NOT_ASSESSED`, making absence of assessment explicit rather than treating it as failure or compliance.

`ObligationControlMapping` records the reviewed link and rationale. Candidate extraction, evidence requirements, gap analysis and human-review state transitions are deferred to later v0.4.x releases.

## Release line

- v0.4.0: obligation → control contract and reviewed mappings
- v0.4.1: control → evidence requirements and records
- v0.4.2: evidence gap / regulatory impact analysis
- v0.4.3: human review and audit trail
- v0.4.4: workflow benchmark and end-to-end scenario
