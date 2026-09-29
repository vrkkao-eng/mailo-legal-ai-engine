# Architecture boundaries

The portfolio uses separate repositories and layers so that legal knowledge,
application workflow, and reasoning-system experiments are not duplicated.

## Ownership

| Capability | Mailo-ontology | mailo-legal-ai-engine | adaptive-kg-reasoning |
| --- | --- | --- | --- |
| Canonical legal concepts and relations | **owns** | consumes | no |
| Substantive SHACL legal constraints | **owns** | executes selected releases | no |
| Legal-source annotations | **owns** | consumes / records application provenance | no |
| Regulatory source/version workflow models | no | **owns** | no |
| Regulatory change detection | no | **owns** | no |
| Retrieval and citation evaluation | no | **owns** | no |
| Obligation/applicability workflow | represents legal concepts where needed | **owns application logic** | no |
| Controls, evidence, human review | no | **owns** | no |
| HTTP API / service / Docker | no | **owns** | optional only for its own experiments |
| Incremental reasoning research | no | may consume a mature interface later | **owns** |
| Materialisation/placement experiments | no | may consume later | **owns** |

## MAILO ontology boundary

`Mailo-ontology` remains the source of record for canonical RDF/OWL concepts,
legal-source annotations, substantive SHACL shapes, and ontology releases.

Do not move application state into the ontology merely because it can be
represented as RDF. Examples that stay in the application layer include:

- review status;
- assigned reviewer;
- evidence-upload state;
- remediation tasks;
- API request metadata;
- model confidence;
- workflow timestamps.

## Legal AI Engine boundary

`mailo-legal-ai-engine` owns operational RegAI capabilities:

```text
official sources
    -> version/change records
    -> obligation/applicability workflow
    -> controls/evidence
    -> human review
    -> evaluation/audit
```

It may consume a released MAILO ontology or SHACL profile, but it must not copy
the canonical ontology into an application-specific fork.

## Adaptive KG boundary

`adaptive-kg-reasoning` remains an independent reasoning/systems research
repository. Its roadmap should not be rewritten around MAILO. A mature
reasoning component may later be consumed through a defined interface, but
code or benchmarks should not be copied into the RegAI engine.

## Non-duplication rule

Before creating a new Legal AI / RegAI repository, first ask whether the work
is:

1. canonical legal knowledge -> `Mailo-ontology`;
2. operational RegAI application logic -> `mailo-legal-ai-engine`; or
3. general reasoning-systems research -> `adaptive-kg-reasoning`.

Create a new repository only when the work has a genuinely independent
research question or product boundary that cannot be represented cleanly in
one of those owners.
