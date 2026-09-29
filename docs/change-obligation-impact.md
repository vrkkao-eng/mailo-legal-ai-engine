# Change-to-obligation candidates — v0.3.1

v0.3.1 links reviewed regulatory changes to obligations conservatively.

An impact candidate means **review this obligation in light of this change**. It does not mean that the obligation's legal meaning, scope, or applicability has changed.

The first implementation requires the same regulatory source and provision. An exact canonical locator produces `LOCATOR_MATCH`. A shared provision with different paragraph/point detail produces `REVIEW_REQUIRED`. Different instruments or different provisions are not linked by this deterministic rule.

Every generated candidate starts with `reviewed = false`. The engine therefore preserves the distinction between a reviewed regulatory change, a deterministic candidate relationship to an obligation, and a later human-reviewed impact determination.

Semantic expansion, ontology-mediated relationships, or LLM candidate generation may be evaluated later, but must not silently convert candidate links into legal conclusions.
