# Engineering profile

## What this repository demonstrates

**MAILO Legal AI Engine** is a public Python application layer for structured legal knowledge, explicit validation, and reproducible research workflows.

The engineering evidence in this repository is intentionally narrower than the original private thesis tooling. It demonstrates:

- packaged Python CLI workflows;
- structured RDF/JSON-LD export;
- reviewed SPARQL query execution;
- explicit SHACL validation;
- reproducible validation reports with input/shape hashes;
- optional constrained LLM tool use on supplied material;
- pytest regression tests; and
- FastAPI endpoints for local graph export, synthetic-shape validation, and reviewed SPARQL queries;
- Docker/Compose API scaffolding; and
- GitHub Actions CI with Python 3.11–3.13, API tests, wheel build, clean-environment CLI smoke testing, and container health smoke testing.

It does **not** claim production deployment, vector retrieval, independent legal verification, or publication of the original private multi-agent workflow.

## Five-minute walkthrough

1. Run the offline demo:
   ```bash
   mailo demo --output artifacts/demo
   ```

2. Inspect:
   - exported JSON-LD / Turtle;
   - the synthetic instance graph;
   - SHACL JSON / Turtle / Markdown reports; and
   - SHA-256 input/shape hashes.

3. Run validation directly:
   ```bash
   mailo validate \
     --instance mailo_cli/resources/system.json \
     --shapes mailo_cli/resources/demo-shapes.ttl \
     --output artifacts/validation
   ```

4. Run a packaged SPARQL query against a selected MAILO ontology release.

5. Open the GitHub Actions workflow and show:
   - multi-version Python testing;
   - wheel build;
   - installation outside the checkout; and
   - CLI and API tests; and
   - container `/health` smoke testing.

The point of the demonstration is not to claim automated legal decision-making. It is to show how a domain requirement becomes explicit input, a graph representation, a testable constraint, a machine-readable result, and a documented limitation.

## Engineering story

### Knowledge representation

The companion [MAILO ontology](https://github.com/vrkkao-eng/Mailo-ontology) owns the canonical legal knowledge model, legal-source annotations, and substantive SHACL shapes.

### Application layer

This repository owns the reusable Python layer:

```text
supplied findings / source URLs
        |
        v
optional constrained LLM tool loop
        |
        v
structured findings
        |
        +--> RDF / JSON-LD export
        |
        +--> reviewed SPARQL execution

system JSON + explicit shapes
        |
        v
RDFLib + pySHACL
        |
        v
structured reports + hashes
```

The optional local API is a thin adapter over those existing workflows. It
exposes health/readiness checks and graph, hash-pinned trusted-shapes
validation, and reviewed SPARQL endpoints; `/research` remains CLI-only. The API does not
introduce a vector database, retrieval system, or legal-decision endpoint.

### Validation boundary

The architecture deliberately keeps model-assisted structuring separate from SHACL validation. LLM output is not automatically converted into a legal-compliance conclusion.

## Recruiter-facing project description

> **MAILO Legal AI Engine — Python application layer for traceable legal-AI workflows.**  
> Built and tested a public Python package integrating source-linked RDF/JSON-LD export, optional constrained LLM tool use, SPARQL execution, and SHACL validation, with reproducible reports, pytest coverage, and GitHub Actions CI.

## CV-ready bullet

> Built a Python legal-AI research engine integrating source-linked RDF/JSON-LD export, optional LLM tool use, reviewed SPARQL queries, SHACL validation, automated tests, and CI; documented the boundary between machine conformance and legal interpretation.

## Implemented now

- Python 3.11+ package and CLI
- RDFLib
- RDF / JSON-LD export
- reviewed SPARQL SELECT queries
- pySHACL validation
- JSON / Turtle / Markdown validation reports
- SHA-256 input and shapes-file hashes
- optional Anthropic-backed constrained tool loop
- optional FastAPI service layer with Pydantic request/response contracts
- operator-configured, SHA-256-pinned external SHACL shape profiles
- conservative API controls: request-size limit, timeout, disabled-by-default CORS, request IDs, and JSON access logs
- Docker API image and Compose configuration
- pytest regression suite
- GitHub Actions CI, including API and container health smoke tests
- wheel build and installed-package smoke test

## Next engineering increments

These are planned improvements, not current implementation claims:

1. **Vector retrieval / Qdrant**
   Add legal-document retrieval only after defining an evaluation corpus, citation expectations, and failure cases.

2. **Retrieval evaluation**
   [A candidate question/source seed](retrieval-evaluation-seed.md) exists. Build and adjudicate the corpus, then compare graph-only retrieval with vector-supported retrieval using measurable recall and source-support criteria. No benchmark results exist yet.

3. **Service hardening**
   Add authentication, process-level resource limits, deployment observability, and operational alerting.

## Portfolio placement

Use this repository together with [Mailo-ontology](https://github.com/vrkkao-eng/Mailo-ontology):

- **Mailo-ontology** demonstrates legal knowledge modelling, RDF/OWL, SPARQL, SHACL, and source-grounded constraint design.
- **mailo-legal-ai-engine** demonstrates Python application engineering, packaging, validation, testing, and CI.

Together they support an **Applied AI / Knowledge Engineering / Legal AI** narrative without presenting research prototypes as production systems.
