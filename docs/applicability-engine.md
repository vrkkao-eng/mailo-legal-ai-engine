# Applicability engine — v0.3.2

v0.3.2 evaluates **reviewed factual gates** against a supplied system description. It does not ask an LLM to decide whether law applies.

Supported deterministic gates are actor role, system kind, and explicit fact presence.

The engine distinguishes closed-world fields from open-world facts. A supplied actor role or system kind can fail a reviewed gate and produce `DOES_NOT_APPLY`. Absence of an open-world fact is not treated as false: it produces `REVIEW_REQUIRED` and records the missing fact.

Only when every reviewed gate is satisfied does the engine return `APPLIES`.

This is a scoped application-layer assessment, not a general legal conclusion. Interpretive questions, unsupported factual predicates, exceptions, temporal complexity, and unresolved legal classification must remain reviewable rather than being forced into binary output.
