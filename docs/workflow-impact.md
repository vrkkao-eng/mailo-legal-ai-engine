# v0.4.2 — Evidence gaps and regulatory-impact propagation

v0.4.2 connects the reviewed workflow layers introduced in v0.3.x–v0.4.1.

```text
RegulatoryChange
    -> ObligationImpactCandidate
    -> reviewed ObligationControlMapping
    -> Control
    -> EvidenceRequirement
```

It also identifies evidence requirements for which the supplied `EvidenceSet`
contains no registered record.

## Evidence-gap semantics

`find_evidence_gaps()` returns only requirements without registered records.

- `MANDATORY_NO_RECORD`: no record is registered for a reviewed mandatory requirement.
- `OPTIONAL_NO_RECORD`: no record is registered for a reviewed optional requirement.

These statuses describe the supplied inventory only. They do not establish that
evidence does not exist elsewhere, that supplied evidence would be sufficient,
that a control failed, or that an organisation is non-compliant.

Requirements with registered records are not emitted as positive findings.
v0.4.2 therefore does not create a "pass" state from document presence.

## Regulatory-impact semantics

`propagate_regulatory_change()` reuses the conservative v0.3.1
change-to-obligation linker, then follows only reviewed
obligation-to-control mappings.

Every downstream result is `REVIEW_REQUIRED`. The function preserves the
upstream locator-link status so callers can distinguish an exact locator match
from a broader same-provision review candidate.

If an affected obligation has no reviewed control mapping, the obligation-level
review candidate is preserved instead of silently dropping the impact.

Propagation means:

> an upstream legal source changed, so linked organisation-owned workflow
> artefacts should be re-examined.

It does not mean that a control or evidence requirement is obsolete, deficient,
or legally incorrect.

## Integrity checks

Propagation rejects:

- duplicate obligation IDs;
- duplicate control IDs;
- mappings to unknown obligations or controls;
- a control whose obligation ID conflicts with its reviewed mapping; and
- evidence requirements that reference controls outside the supplied workflow.

The reviewed fixtures also use a shared canonical AI Act source identifier
(`eu-ai-act`) so the change and obligation layers can be joined deterministically.

## Deferred to v0.4.3+

v0.4.2 does not add:

- evidence sufficiency or authenticity assessment;
- freshness/expiry policy;
- control effectiveness assessment;
- compliance or risk scores;
- reviewer approval/rejection;
- remediation tasks;
- escalation state;
- audit-event history; or
- LLM-generated impact conclusions.
