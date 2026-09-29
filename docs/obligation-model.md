# Obligation representation — v0.3.0

v0.3.0 opens the obligation/applicability release line. It defines the application-layer contract before adding extraction or automated applicability logic.

## Obligation unit

A reviewed obligation records:

- source and locator;
- actor;
- action;
- object;
- modality;
- optional legal condition;
- optional effective-date condition;
- optional link to a canonical MAILO concept.

This is deliberately smaller than a full legal-rule language. Its purpose is to give later RegAI components a stable interface.

## Applicability contract

Applicability uses three states:

- APPLIES;
- DOES_NOT_APPLY;
- REVIEW_REQUIRED.

REVIEW_REQUIRED must identify missing facts. The system therefore has an explicit abstention path rather than forcing a binary legal answer when the factual or interpretive basis is incomplete.

## Authority boundary

The application model does not replace MAILO ontology concepts, infer legal holdings, or convert LLM output directly into reviewed obligations. Candidate extraction and evaluation belong to later v0.3.x increments.

v0.3.0 also does not map obligations to organisational controls or evidence. That remains v0.4.x.
