# v0.4.1 — Control evidence requirements and records

v0.4.1 extends the organisation-facing workflow from reviewed controls to
reviewed evidence expectations and registered evidence artefacts.

## Contract

`EvidenceRequirement` records what evidence an organisation expects for a
reviewed control. It is workflow design data and does not imply that the legal
source explicitly mandates a particular file, document, or artefact.

`EvidenceRecord` records a supplied artefact with provenance metadata:
identifier, requirement, type, HTTPS source URI, SHA-256, collection timestamp,
and owner role.

`EvidenceSet` validates internal referential integrity and evidence-type
consistency. It does not decide whether evidence is sufficient, current,
credible, or legally adequate.

## Important boundary

The following implications are deliberately invalid:

```text
record exists
    != evidence is sufficient
    != control is effective
    != obligation is satisfied
    != organisation is compliant
```

Absence of an evidence record is represented as absence. v0.4.1 does not create
a synthetic `MISSING` evidence object or compliance status. Evidence-gap
classification belongs to v0.4.2.

## Provenance

Evidence records require:

- an absolute HTTPS source URI;
- a lowercase SHA-256 digest;
- a timezone-aware collection timestamp; and
- an organisation owner role.

These fields support auditability and identity of the registered artefact; they
do not establish authenticity or substantive evidential quality.

## Release boundary

Included in v0.4.1:

- reviewed evidence requirements;
- registered evidence records;
- controlled evidence types;
- provenance validation;
- requirement/record referential integrity;
- type consistency;
- reviewed seed fixture and regression tests.

Deferred:

- evidence sufficiency;
- freshness policies;
- gap classification;
- risk/compliance scores;
- human approval/rejection;
- escalation/remediation workflows;
- LLM-generated evidence requirements.
