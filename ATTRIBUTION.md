# Attribution and provenance

Author and original project owner: **Victor (Chang-Hua) Kao**.

Selected code was extracted from the owner's private `vrkkao-eng/DH_THESIS`,
commit `80f387bda1055c25e89797c9be635f1aad9ab8d5` (CLI version 5.0.0).
The source `pyproject.toml` declares MIT licensing and names Victor Kao.
[Source blob identifiers](docs/extraction-manifest.json) identify the reviewed files.
The private history is not included because it also contains unpublished materials.

Source commits record Claude co-authorship, including Claude Sonnet 4.6.
The original tooling was AI-assisted; this repository does not imply sole manual
authorship or independent third-party validation. The public extraction,
hardening, new synthetic tests and documentation were prepared with Codex assistance.

## Retained and adapted

- BaseAgent tool-use loop, finding collection, cache and output helpers.
- KnowledgeGraphExporter JSON-LD context, category mapping and export method.
- CLI boundaries, JSON-system mapping and pySHACL validation flow.
- Five SPARQL SELECT templates.
- Selected original BaseAgent and JSON-LD exporter tests.

## Changes for the public engine

Private specialist prompts and retrieval integrations were removed.
The public prompt is newly written and uses supplied text only.
The LLM call runs off the event-loop thread; incomplete and exhausted runs fail.
Exports preserve full text, declared source IRIs and year datatypes, using
content-derived IDs. RDFLib serializes instance terms. Validation retains all
SHACL results and records input hashes. Namespace and query behavior are aligned
with the public ontology; documentation distinguishes conformance from legal validity.

## Other projects

[MAILO ontology](https://github.com/vrkkao-eng/Mailo-ontology) is by C.-H. Kao,
released separately under CC BY 4.0. Cite its selected release, for example:
Kao, C.-H. *MAILO — Medical AI Legal Ontology*, v5.2.3, https://w3id.org/mailo#.
No ontology release or substantive shapes are relicensed as MIT here.

RDFLib, pySHACL, Click, Rich, Anthropic's Python SDK and development tools remain
their respective authors' work under their own licences; they are dependencies,
not original components claimed by this project.
