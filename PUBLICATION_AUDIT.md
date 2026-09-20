# Public extraction audit

Reviewed on 2026-09-20 against private source commit
`80f387bda1055c25e89797c9be635f1aad9ab8d5`.
This is a new, selected-file repository, not a fork containing thesis history.
The earlier synthetic-only scaffold was replaced by a source-derived implementation.

## File decisions

| Source area | Decision and evidence |
| --- | --- |
| `.env.example` | Reviewed: placeholder/empty API values plus thesis/Overleaf configuration. Replaced with empty optional Anthropic/model variables only. |
| `.mcp.json` | Reviewed: contains a personal email, an absolute Windows path and placeholder keys. Excluded; the engine needs no MCP server. |
| `config/agents.yaml` | Reviewed: specialist prompt paths, research-search settings and optional institutional integrations. Excluded. CLI arguments and documented environment variables are the public configuration. |
| `agents/base_agent.py` | Selected common methods retained. Removed contact identifiers, specialist language instruction and all network retrieval tools. Public loop exposes only save_finding; source membership is checked. |
| Specialist agents / orchestrator | Excluded: contain research-specific prompts and dependencies on private workflow. No claim that the original multi-agent pipeline was published wholesale. |
| Graph exporter | JSON-LD context, mapping and export logic retained and repaired. D3/HTML and Cypher exporters excluded to keep the runtime small and avoid unrelated output surfaces. |
| Ontology exporter | Excluded: embeds a historical ontology/schema and research assertions. Canonical ontology stays in its own repository. |
| validate / CLI | Source-derived flows refactored. Removed hard-coded legal remediation text, misleading compliance labels, hard-coded shape counts and result suppression. |
| Original tests | BaseAgent and JSON-LD exporter tests adapted. Private SHACL tests/fixtures reviewed: synthetic, but tied to old namespace and historical substantive shapes; replaced by synthetic engine regression tests. No private fixture copied. |
| queries | All five SELECT templates reviewed and retained with canonical namespace; corrected tension-label aggregation and clarified applicability/patent-query limits. |
| tools | Existing inventory primarily supports thesis, bibliography, figures, HTML/PDF generation. Excluded. Added a small installed-package example validator. |
| pyproject | Original author and MIT declaration verified. Narrowed dependencies and explicit package-data configuration; removed personal email and thesis-review extras. |
| New samples | Fictional text, example.org URLs and a synthetic SHACL rule only. |

## Excluded from publication

Thesis TeX/BibTeX, drafts, appendices, figures, logos, Overleaf sync and history;
research outputs, corpora, literature-search results, personal materials, agent
prompts, MCP configurations, credentials, local environments, caches and large
binary/document files. Only the allowlisted working files enter the new Git tree.

## Verification scope

Source attribution is recorded in ATTRIBUTION.md and source blob hashes in
docs/extraction-manifest.json. Tests cover the exported engineering behavior with
synthetic data and mocked model responses. No live API key was used. A pattern scan
and manual review of the publication tree supplement the allowlist; these are not a
claim that all possible secrets in the original private repository were audited.

The engine references a public ontology release without bundling its CC BY assets.
Generated reports and external ontology checkouts are ignored by Git.
