# Deterministic structural diff — v0.2.1

v0.2.1 adds a deliberately narrow comparison layer for already-normalised regulatory provision units.

## Input contract

Each input unit contains a `SourceLocator` and the text assigned to that locator in one selected version. The comparator normalises whitespace and computes SHA-256 over the normalised text. Stable locator identity is the primary alignment key.

## Output candidates

The comparator emits `TEXT_CHANGED` when the same locator has different normalised text, `DELETED` when an old locator is absent from the new set, and `ADDED` when a new locator is absent from the old set. A changed-text candidate also records a deterministic `SequenceMatcher` similarity score for diagnostics. The score is not a legal-materiality score.

## Deliberate non-inference

Although the v0.2 data model can represent `RENUMBERED` and `DATE_CHANGED`, v0.2.1 does not infer them from raw text. A deleted unit and a similar added unit do not prove renumbering, and a changed date string does not by itself establish the legal effect or application date of an amendment. Those relationships require reviewed amendment metadata or a later source-aware alignment step.

## No legal conclusion

The output is a set of structural change candidates. It does not determine legal materiality, applicability, compliance, or required controls. This preserves the boundary between deterministic document engineering (v0.2.x) and obligation/applicability reasoning (v0.3.x).
