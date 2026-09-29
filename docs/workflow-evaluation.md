# v0.4.4 — Workflow evaluation and fixed end-to-end scenario

v0.4.4 closes the v0.4.x workflow line with deterministic evaluation rather than
new legal or compliance logic.

## Fixed scenario

The bundled scenario follows one reviewed FRIA path:

```text
AI Act Article 27(4) change
    -> reviewed obligation
    -> reviewed control
    -> four evidence requirements
    -> two registered evidence records
    -> one mandatory evidence gap
    -> one optional evidence gap
    -> one regulatory-impact candidate
    -> selective routing
    -> focused human review
    -> audit trail / escalation
```

Expected routing:

- mandatory evidence gap -> `HUMAN_REVIEW` / AI governance;
- optional evidence gap -> `LOG_ONLY`;
- regulatory-impact candidate -> `HUMAN_REVIEW` / Legal.

The regulatory-impact review uses `UNKNOWN` and is escalated. The benchmark
therefore exercises the abstention-safe path rather than a happy-path-only
workflow.

## Workflow benchmark

`WorkflowBenchmarkReport` measures:

- routing accuracy against a reviewed fixed gold set;
- route traceability completeness;
- human-review and log-only counts;
- human-review share;
- audit-trace completeness;
- escalation integrity;
- unsafe UNKNOWN resolution count.

It also reports:

- mean context-reference count per human-review question;
- mean question length in characters.

These two fields and `human_review_share` are **workflow burden proxies**.
They are engineering descriptors only. They are not measurements of cognitive
load, reviewer effort, automation bias, or human performance.

## Safety boundary

The evaluation does not calculate:

- legal correctness;
- compliance scores;
- control effectiveness;
- evidence sufficiency;
- reviewer competence;
- cognitive load;
- automation-bias reduction.

The fixed scenario sets
`compliance_determination_produced = false` and the CLI output preserves that
boundary.

## CLI

Run the complete offline workflow with:

```bash
mailo workflow-demo
```

The command emits machine-readable JSON containing the scenario counts and
benchmark report. It requires no API key and does not call an LLM.

## Relation to later work

v0.4.4 is a deterministic engineering benchmark on a small reviewed fixture.
Human-subject measures such as decision accuracy, verification behaviour,
metacognition, cognitive load, or automation bias require a separate empirical
study and are outside this release.
