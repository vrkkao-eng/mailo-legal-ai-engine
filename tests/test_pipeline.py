import json
import pytest
from rdflib import Graph, Literal, Namespace, RDF, XSD
from mailo_cli.pipeline import export_findings, validate_findings
from mailo_cli.validate_cmd import build_turtle, parse_violations, MAILO, SH, run_shacl


def finding(**changes):
    return {
        "category": "case_law",
        "title": "Same title",
        "content": "Synthetic",
        "source_url": "https://example.org/source",
        **changes,
    }


def test_missing_source_rejected():
    with pytest.raises(ValueError, match="source_url"):
        validate_findings([finding(source_url="")])


def test_credential_url_rejected():
    with pytest.raises(ValueError):
        validate_findings([finding(source_url="https://user:password@example.org")])


def test_same_title_different_sources_distinct_nodes(tmp_path):
    export_findings(
        [finding(), finding(source_url="https://example.org/second")], tmp_path
    )
    doc = json.loads((tmp_path / "medical_ai_knowledge_graph.jsonld").read_text())
    assert len({n["@id"] for n in doc["@graph"]}) == 2
    g = Graph().parse(tmp_path / "findings.ttl")
    assert len(list(g.subjects(RDF.type, MAILO.CJEUCase))) == 2


def test_full_text_and_year_survive_rdf_export(tmp_path):
    content = "A" * 900
    export_findings([finding(content=content, metadata={"year": "2026"})], tmp_path)
    g = Graph().parse(tmp_path / "findings.ttl")
    dc = Namespace("http://purl.org/dc/terms/")
    assert Literal(content) in g.objects(None, dc.description)
    assert Literal("2026", datatype=XSD.gYear) in g.objects(None, dc.date)


def test_turtle_escapes_labels_and_identifiers():
    data = {"system_id": "test> . <evil", "label": 'Quoted " label\nnewline'}
    g = Graph().parse(data=build_turtle(data), format="turtle")
    assert len(g) == 3


def test_boolean_string_is_not_truthy():
    with pytest.raises(ValueError, match="Boolean"):
        build_turtle({"system_id": "x", "has_defined_scope": "false"})


def test_missing_oversight_is_not_invented():
    g = Graph().parse(
        data=build_turtle({"system_id": "x", "oversight": {}}), format="turtle"
    )
    assert not list(g.triples((None, MAILO.oversightIsSubstantive, None)))


def test_unknown_fields_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        build_turtle({"system_id": "x", "hidden_typo": True})


def test_results_are_not_silently_dropped():
    from rdflib import BNode

    g = Graph()
    for severity in (SH.Violation, SH.Warning, SH.Info):
        result = BNode()
        g.add((result, RDF.type, SH.ValidationResult))
        g.add((result, SH.sourceShape, BNode()))
        g.add((result, SH.resultSeverity, severity))
        g.add((result, SH.resultMessage, Literal("Unknown rule")))
        g.add((result, SH.value, Literal(False)))
    results = parse_violations(g)
    assert len(results) == 3
    assert all(r["value"] == "false" for r in results)
    assert {r["severity"] for r in results} == {
        str(SH.Violation),
        str(SH.Warning),
        str(SH.Info),
    }


def test_empty_shapes_rejected(tmp_path):
    path = tmp_path / "empty.ttl"
    path.write_text("")
    with pytest.raises(ValueError, match="no declared"):
        run_shacl(build_turtle({"system_id": "x"}), path)
