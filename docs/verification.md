# Verification evidence

Local verification on 2026-09-20, Python 3.12.14:

- 30 automated tests passed, including mocked model tool use and negative cases.
- Synthetic CLI example produced graph exports and conforming SHACL reports.
- Package installation succeeded; GitHub Actions additionally checks an installed wheel outside the checkout.
- No live Anthropic request was made. Model quality and current model availability are not verified.

## External ontology integration

Tested public Mailo-ontology tag v5.2.3, without copying its files into this repository:

| Artifact | Git blob SHA |
| --- | --- |
| docs/ontology.ttl | ad0c13aa8b41f5ec279f1075e517e0740343c64a |
| docs/mailo_shacl_shapes.ttl | 0693975842a81c60cfe390335db25d7d278595fa |

RDFLib parsed 1,946 triples. The ontology graph conformed to the supplied public shapes with inference disabled. This checks machine conformance, not the truth of legal assertions.

| Packaged query | Result rows |
| --- | ---: |
| cjeu_chain | 7 |
| frameworks | 8 |
| fto_patent | 6 |
| obligations_samd | 0 |
| tensions | 18 |

These are query-result row counts, not independently verified entity counts. Joins, comments and status values may produce multiple rows per entity. Zero obligation rows are retained and documented, not filled with invented results.

RDFLib/pySHACL emit dependency deprecation warnings in the local environment. They do not fail these tests. CI run results remain the authority for the tested Linux/Python matrix.
