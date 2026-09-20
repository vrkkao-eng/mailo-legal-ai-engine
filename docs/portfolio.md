# FDE portfolio connection

## A defensible project description

**MAILO Legal AI Engine — Python research tooling for structured legal knowledge.**

Extracted reusable Python components from a private research project into a
public package: CLI workflows, an optional model/tool loop, source-linked JSON-LD
and Turtle export, explicit SHACL validation, structured reports and automated
tests. Kept the ontology and substantive legal shapes in a separate versioned
repository. Development was AI-assisted.

Do not describe the full private multi-agent system, production deployment,
retrieval accuracy or independent legal verification as demonstrated here.

## Five-minute demonstration

1. Run `mailo demo` without credentials.
2. Show the source URL, JSON-LD output and SHACL report hashes.
3. Set the synthetic review flag to false, rerun validation, and show the failure
   exit code and anonymous-shape result.
4. Run a packaged SPARQL query against the selected public ontology release.
5. Show the tests and GitHub Actions run; explain why model quality and legal
   validity require separate evaluation.

This supports the functional-requirements-to-implementation discussion:
how a domain statement becomes explicit input, a graph term, a testable constraint,
an actionable report and a documented limitation.

## Portfolio placement

Pair this repository with Mailo-ontology:
- **Knowledge representation:** ontology modelling, source annotations and shapes.
- **Engineering implementation:** Python packaging, CLI integration, reproducible
  synthetic examples, error handling and automated tests.

A concise CV bullet, after confirming the published CI result:
“Extracted and tested a Python legal-AI research engine integrating source-linked
RDF export, optional LLM tool use, SPARQL queries and SHACL validation; documented
the boundary between machine conformance and legal interpretation.”

## Next builds, not current claims

1. Add a small authorised document corpus and an evaluation set with citations,
   expected answers and failure cases. Measure extraction and source support.
2. Add a thin FastAPI service with explicit input limits, authentication and
   error contracts; containerise it and test the API in CI.
3. Compare graph-only retrieval with an optional vector index only after defining
   retrieval metrics and a reproducible evaluation protocol.

For Netcompany's legal-document / knowledge-retrieval narrative, use the existing
CLI and validation evidence now; present API deployment and vector retrieval as
a future engineering increment until implemented.
