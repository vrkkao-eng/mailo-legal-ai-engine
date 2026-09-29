# Obligation/applicability evaluation — v0.3.3

v0.3.3 closes the v0.3.x line with explicit measurement of applicability status, abstention behaviour, and missing-fact disclosure.

The benchmark reports **status accuracy**, **abstention accuracy** on cases whose reviewed answer is REVIEW_REQUIRED, and **missing-fact completeness**. A system that forces APPLIES or DOES_NOT_APPLY where the gold case requires review is therefore penalised rather than rewarded for producing a binary answer.

The initial gold file is a small regression seed. Its scores are not evidence of general legal-applicability accuracy.

Together, v0.3.0–v0.3.3 establish a reviewed obligation contract, conservative change-to-obligation candidates, deterministic factual gates with open-world abstention, and measurable evaluation. Organisational control/evidence workflow remains v0.4.x.
