# Retrieval evaluation seed (candidate, not a benchmark)

[`evals/retrieval_seed.json`](../evals/retrieval_seed.json) is a small, manually drafted set of 15 questions against seven public EU documents. It records candidate source and section/paragraph locators for future retrieval experiments. It contains **no downloaded corpus, extracted passages, adjudicated relevance judgments, retriever, vector database, baseline scores, or legal-answer key**. No retrieval performance claim can be made from this file.

## Scope and source boundaries

The selected sources are the AI Act, MDR, GDPR, two MDCG guidance documents, and two CJEU judgments. Source URLs and exact versions are in the JSON catalog. The AI Act target is the EUR-Lex consolidated text dated 2026-07-27; the MDR target is the consolidated text dated 2026-01-01; the GDPR target is its 2016 Official Journal text. These are deliberately fixed *retrieval snapshots*, not a guarantee that a rule is currently applicable to a given system. Before using any legal proposition, check amendments, corrigenda, commencement/transitional provisions, and the authentic Official Journal acts. EUR-Lex consolidated texts are documentary aids.

MDCG 2019-11 rev.1 and MDCG 2025-6 are **non-binding guidance**, not legislation. The selected SCHUFA and Dun & Bradstreet Austria judgments concern **credit scoring/profiling**, not medical-device classification or MDR compliance. They are included only to test retrieval of GDPR-related reasoning and resistance to a false medical-AI premise. Do not promote a guidance statement or analogy into a binding, case-specific legal conclusion.

## Annotation contract

Each question has `support_expected` and zero or more candidate `targets` (`source_id` plus locator). `support_expected: false` means the selected corpus does not support the requested conclusion; `related_sources` names likely distractors, not positive evidence. The locators identify where a reviewer should inspect, not a fully adjudicated passage-level gold label. For the multi-source item R13, both targets are required. The negative items R14–R15 require an explicit insufficiency/false-premise outcome if an answer-generation stage is later evaluated; a retrieval-only run should still inspect any returned passages for unsupported claims.

Before scoring, a legal-domain reviewer should verify each target against the pinned source, resolve acceptable alternative passages, mark the minimum evidence span, and approve wording in a versioned annotation file. Keep source authority, interpretation, modelling choice, and executable validation results separate. A SHACL pass is not proof of legal compliance.

## Suggested next experiment

1. Acquire and hash the seven version-pinned documents, recording licensing, source URL, access date, and extraction method. Do not commit large source copies without checking reuse terms.
2. Build comparable source chunks with document ID, version, section/paragraph locator, and stable chunk ID. Audit PDF text extraction and section boundaries.
3. Have independent reviewers adjudicate the candidate targets and false-premise items. Record disagreements and allowed alternate passages.
4. Run a simple lexical baseline before testing graph-only or vector-assisted retrieval. Score source-level and locator-level Recall@k and MRR; inspect citation support and abstention separately. Fix `k`, corpus, chunking, and query set before comparisons.
5. Report errors by source type, outdated-version mismatch, multi-source omission, and unsupported legal conclusion. Only then consider a larger corpus or Qdrant.

The JSON is a planning fixture. It is intentionally not loaded by the existing CLI or API and changes no validation behavior.
