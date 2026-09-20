import hashlib
import json

from fastapi.testclient import TestClient

import mailo_cli.api as api
from mailo_cli.shape_registry import ShapeRegistry


app = api.app


client = TestClient(app)


def test_health_and_ready():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_graph_uses_existing_export_pipeline():
    response = client.post(
        "/graph",
        json={"findings": [{
            "category": "case_law", "title": "Synthetic", "content": "Text",
            "source_url": "https://example.org/source",
        }]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["findings"] == 1
    assert body["triples"] > 0
    assert "mailo:CJEUCase" in body["turtle"]


def test_validate_keeps_conformance_boundary_and_allows_nonconformance():
    response = client.post(
        "/validate",
        json={"system": {
            "system_id": "Synthetic", "classes": ["MedicalAISystem"],
            "individual_non_automated_review": False,
        }},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conforms"] is False
    assert body["results"]
    assert body["shapes_profile"] == "demo"
    assert len(body["shapes_sha256"]) == 64
    assert "not a legal compliance determination" in body["scope"]


def test_validate_uses_hash_pinned_operator_profile(tmp_path, monkeypatch):
    shapes = tmp_path / "reviewed-shapes.ttl"
    shapes.write_text(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix mailo: <https://w3id.org/mailo#> .\n"
        "@prefix ex: <https://example.org/> .\n"
        "ex:Shape a sh:NodeShape; sh:targetClass mailo:MedicalAISystem .\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(shapes.read_bytes()).hexdigest()
    manifest = tmp_path / "shapes.json"
    manifest.write_text(json.dumps({"profiles": {"mailo-test-v1": {
        "file": "reviewed-shapes.ttl", "sha256": digest,
        "scope": "Conformance to an operator-registered test shape; not legal advice",
    }}}), encoding="utf-8")
    monkeypatch.setattr(api, "_SHAPE_REGISTRY", ShapeRegistry(api._RESOURCE_DIR, str(manifest)))

    response = client.post(
        "/validate",
        json={"shapes": "mailo-test-v1", "system": {"system_id": "x"}},
    )
    assert response.status_code == 200
    assert response.json()["shapes_profile"] == "mailo-test-v1"
    assert response.json()["shapes_sha256"] == digest


def test_registry_rejects_modified_trusted_shape(tmp_path):
    shapes = tmp_path / "reviewed-shapes.ttl"
    shapes.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .", encoding="utf-8")
    digest = hashlib.sha256(shapes.read_bytes()).hexdigest()
    manifest = tmp_path / "shapes.json"
    manifest.write_text(json.dumps({"profiles": {"mailo-test-v1": {
        "file": "reviewed-shapes.ttl", "sha256": digest, "scope": "test",
    }}}), encoding="utf-8")
    registry = ShapeRegistry(api._RESOURCE_DIR, str(manifest))
    shapes.write_text("changed", encoding="utf-8")

    try:
        registry.get("mailo-test-v1")
    except ValueError as exc:
        assert "changed on disk" in str(exc)
    else:
        raise AssertionError("Modified trusted shapes must be rejected")


def test_validate_rejects_unknown_system_fields_safely():
    response = client.post("/validate", json={"system": {"system_id": "x", "typo": True}})
    assert response.status_code == 400
    assert "Unknown system fields" in response.json()["detail"]


def test_sparql_uses_only_packaged_query_names():
    response = client.post(
        "/sparql",
        json={
            "ontology_turtle": "@prefix m: <https://w3id.org/mailo#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . m:Demo a m:EURegulation; rdfs:label \"Synthetic\"@en .",
            "built_in": "frameworks",
        },
    )
    assert response.status_code == 200
    assert response.json()["rows"][0]["framework"] == "https://w3id.org/mailo#Demo"
    invalid = client.post(
        "/sparql",
        json={"ontology_turtle": "@prefix m: <https://w3id.org/mailo#> .", "built_in": "DROP ALL"},
    )
    assert invalid.status_code == 422
