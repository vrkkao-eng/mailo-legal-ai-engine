# Regulatory Change Intelligence benchmark — v0.2.3

v0.2.3 closes the v0.2.x line with measurable evaluation rather than another architecture layer.

## Metrics

- **precision** — reviewed matches / all machine candidates.
- **recall** — reviewed matches / all reviewed changes.
- **F1** — harmonic mean of precision and recall.
- **locator accuracy** — candidates aligned to a compatible reviewed locator pair / all candidates.
- **exact type accuracy** — exact candidate type matches / all matched changes.
- **reviewed type coverage** — exact or reviewed-refined matches / all reviewed changes.

A TYPE_REFINED reconciliation counts as a detected change for precision and recall, but not as an exact type match. This reflects the architecture: deterministic comparison can detect a stable-locator text change, while reviewed metadata may refine it to a supported type such as DATE_CHANGED.

## Benchmark scope

The initial gold set is intentionally small and reviewed. It exercises four known amendment patterns already represented in the v0.2.0 fixture. A perfect score on this seed set is a regression result, **not evidence of general legal change-detection performance**.

The benchmark therefore reports capability on a named fixture and must not be presented as a population-level accuracy claim.

## v0.2.x completion criterion

The Regulatory Change Intelligence line now contains version-aware source/change models, deterministic structural candidates, reconciliation against reviewed source metadata, and reproducible evaluation metrics. The v0.3.x line may consume these outputs for obligation and applicability work without changing their evidentiary meaning.
