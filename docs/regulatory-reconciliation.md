# Reviewed change reconciliation — v0.2.2

v0.2.2 connects deterministic structural candidates from v0.2.1 to reviewed regulatory-change records from v0.2.0. The purpose is provenance and review traceability, not automated legal impact assessment.

## Reconciliation states

- **CONFIRMED** — candidate locator pair and type agree with a reviewed record.
- **TYPE_REFINED** — structural evidence identifies a text change, while reviewed source metadata supplies a more specific supported type. The first supported refinement is `TEXT_CHANGED -> DATE_CHANGED`.
- **UNREVIEWED_CANDIDATE** — the deterministic diff found a candidate without compatible reviewed metadata.
- **REVIEWED_ONLY** — a reviewed record has no matching structural candidate in the supplied comparison set.

An unreviewed candidate is never silently promoted to a reviewed change.

## Asymmetric refinement

A structural comparator can observe that text at a stable locator changed. It cannot safely conclude from lexical content alone that the legal relationship is a change in application date. Reviewed amendment metadata can refine that candidate to `DATE_CHANGED`. Machine output cannot override reviewed metadata.

v0.2.2 does not determine affected obligations, actors, systems, controls, or compliance. It also does not infer renumbering from textual similarity.
