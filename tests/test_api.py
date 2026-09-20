from fastapi.testclient import TestClient

from mailo_cli.api import app


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
    assert "not a legal compliance determination" in body["scope"]


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
