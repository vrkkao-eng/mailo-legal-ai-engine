# Retrieval evaluation seed (candidate, not a benchmark)

[`evals/retrieval_seed.json`](../evals/retrieval_seed.json) is a small, manually drafted set of 15 questions against seven public EU documents. It records candidate source and section/paragraph locators for future retrieval experiments. The committed seed contains **no downloaded corpus, extracted passages, adjudicated relevance judgments, or legal-answer key**. An optional offline tool now builds a local PDF/page corpus and exploratory lexical baseline, but this is **not an adjudicated retrieval benchmark**.

## Scope and source boundaries

The selected sources are the AI Act, MDR, GDPR, two MDCG guidance documents, and two CJEU judgments. Source URLs and exact versions are in the JSON catalog. The AI Act target is the EUR-Lex consolidated text dated 2026-07-27; the MDR target is the consolidated text dated 2026-01-01; the GDPR target is its 2016 Official Journal text. These are deliberately fixed *retrieval snapshots*, not a guarantee that a rule is currently applicable to a given system. Before using any legal proposition, check amendments, corrigenda, commencement/transitional provisions, and the authentic Official Journal acts. EUR-Lex consolidated texts are documentary aids.

MDCG 2019-11 rev.1 and MDCG 2025-6 are **non-binding guidance**, not legislation. The selected SCHUFA and Dun & Bradstreet Austria judgments concern **credit scoring/profiling**, not medical-device classification or MDR compliance. They are included only to test retrieval of GDPR-related reasoning and resistance to a false medical-AI premise. Do not promote a guidance statement or analogy into a binding, case-specific legal conclusion.

## Annotation contract

Each question has `support_expected` and zero or more candidate `targets` (`source_id` plus locator). `support_expected: false` means the selected corpus does not support the requested conclusion; `related_sources` names likely distractors, not positive evidence. The locators identify where a reviewer should inspect, not a fully adjudicated passage-level gold label. For the multi-source item R13, both targets are required. The negative items R14–R15 require an explicit insufficiency/false-premise outcome if an answer-generation stage is later evaluated; a retrieval-only run should still inspect any returned passages for unsupported claims.

Before treating any exploratory score as an evaluated result, a legal-domain reviewer should verify each target against the pinned source, resolve acceptable alternative passages, mark the minimum evidence span, and approve wording in a versioned annotation file. Keep source authority, interpretation, modelling choice, and executable validation results separate. A SHACL pass is not proof of legal compliance.

## Remaining evaluation work

1. Audit the locally acquired PDFs, extraction artifacts, source-version labels, and reuse terms. Do not commit source copies or extracted text without checking reuse terms.
2. Build comparable chunks with document ID, version, section/paragraph locator, and stable chunk ID; page numbers alone are insufficient. Audit section boundaries.
3. Have independent reviewers adjudicate the candidate targets and false-premise items. Record disagreements and allowed alternative passages.
4. Fix the corpus, chunking, query set, and `k`, then measure locator-level recall, citation support, and abstention separately. The exploratory source-level lexical scores below are not substitutes.
5. Report errors by source type, outdated-version mismatch, multi-source omission, and unsupported legal conclusion. Only then compare graph-only or vector-assisted retrieval or consider Qdrant.

## Exploratory offline baseline

From the repository root:

```bash
python -m pip install -e ".[dev,retrieval]"
python tools/retrieval_baseline.py prepare --out data/retrieval
python tools/retrieval_baseline.py score --corpus data/retrieval --report data/retrieval/report.json
```

`prepare` downloads only the seven HTTPS PDF URLs in the allowlisted official domains (`eur-lex.europa.eu` and `health.ec.europa.eu`), refuses non-PDF or oversized responses, and checks every file against the SHA-256 pin in the seed before caching it. The pins record the PDFs obtained on 2026-09-20; a changed official PDF requires review and an explicit pin update. The tool records PDF hashes, byte counts, version labels, extraction version, and page counts in `data/retrieval/manifest.json`, and writes page text to `pages.jsonl`. Existing cached PDFs are reused; a changed PDF hash or changed seed requires a fresh output directory. Use `--offline` to require cached PDFs without contacting the network. Official sites may temporarily rate-limit downloads; retry later or reuse a verified local cache. The `data/` directory is ignored by Git: **do not commit the PDFs or extracted text**.

`score` verifies the seed, PDF, and page-text hashes, ranks individual PDF pages by a simple BM25 implementation, and ranks each source by its highest-scoring page. Its report records candidate-gold **source-level** macro Recall@1/3/5, complete source coverage, and reciprocal rank. It excludes the two unsupported/false-premise questions from these positive-retrieval metrics; it does **not** evaluate abstention. A returned PDF page is not necessarily the correct legal paragraph. PDF extraction may also garble characters or section boundaries. Scores are sensitive to this small source selection and question wording, and must not be presented as legal accuracy, passage-level citation quality, or a comparison with vector retrieval.

The tool is intentionally separate from the existing CLI and API and changes no validation behavior. Adjudicated evidence spans, negative-case assessment, a held-out query set, and a stronger baseline are still needed before reporting a retrieval benchmark.
