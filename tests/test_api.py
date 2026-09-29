import hashlib
import json
import pytest

from fastapi.testclient import TestClient

import mailo_cli.api as api
from mailo_cli.regulatory.persistence import SQLiteWorkflowRepository
from mailo_cli.shape_registry import ShapeRegistry
from mailo_cli.settings import ApiSettings, load_api_settings


app = api.app


client = TestClient(app)


def test_health_and_ready():
    health = client.get("/health")
    assert health.json() == {"status": "ok"}
    assert health.headers["x-request-id"]
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["referrer-policy"] == "no-referrer"
    assert client.get("/ready").json() == {"status": "ready"}


def test_declared_oversize_request_is_rejected(monkeypatch):
    monkeypatch.setattr(api, "_SETTINGS", ApiSettings(max_request_bytes=10))
    response = client.post("/graph", content="{" + "x" * 20 + "}")
    assert response.status_code == 413
    assert "size limit" in response.json()["detail"]


def test_service_settings_are_explicit_and_conservative(monkeypatch):
    monkeypatch.setenv("MAILO_MAX_REQUEST_BYTES", "2048")
    monkeypatch.setenv("MAILO_REQUEST_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("MAILO_CORS_ORIGINS", "https://app.example, https://admin.example")
    settings = load_api_settings()
    assert settings.max_request_bytes == 2048
    assert settings.request_timeout_seconds == 12
    assert settings.cors_origins == ("https://app.example", "https://admin.example")


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


def _workflow_payload():
    return {
        "change": {
            "change_id": "ai-act-2026-art-27-4-changed",
            "change_type": "text_changed",
            "source_id": "eu-ai-act",
            "old_version_id": "eu-ai-act-2024-08-01",
            "new_version_id": "eu-ai-act-2026-07-27",
            "effective_date": "2026-07-27",
            "amendment_source_id": "eu-2026-1744",
            "amendment_locator": {
                "provision": "Article 1",
                "paragraph": "13",
                "point": "a",
                "subparagraph": None,
            },
            "source_url": "https://eur-lex.europa.eu/eli/reg/2026/1744/oj",
            "summary": "Reviewed Article 27(4) change.",
            "old_locator": {
                "provision": "Article 27",
                "paragraph": "4",
                "point": None,
                "subparagraph": None,
            },
            "new_locator": {
                "provision": "Article 27",
                "paragraph": "4",
                "point": None,
                "subparagraph": None,
            },
        },
        "obligations": [{
            "obligation_id": "ai-act-art27-fria-review",
            "source_id": "eu-ai-act",
            "locator": {
                "provision": "Article 27",
                "paragraph": "1",
                "point": None,
                "subparagraph": None,
            },
            "actor": "deployer",
            "action": "perform",
            "object": "fundamental rights impact assessment",
            "modality": "must",
            "condition": "where the Article 27 scope conditions are satisfied",
        }],
        "mappings": [{
            "obligation_id": "ai-act-art27-fria-review",
            "control_id": "ctrl-fria-01",
            "rationale": "Reviewed workflow mapping.",
            "reviewed": True,
        }],
        "controls": [{
            "control_id": "ctrl-fria-01",
            "obligation_id": "ai-act-art27-fria-review",
            "title": "Perform and document FRIA",
            "description": "Maintain a documented FRIA workflow.",
            "control_type": "assessment",
            "owner_role": "AI governance",
            "implementation_status": "not_assessed",
            "source": "reviewed mapping",
        }],
        "evidence": {
            "requirements": [
                {
                    "requirement_id": "evreq-fria-record",
                    "control_id": "ctrl-fria-01",
                    "title": "Documented FRIA record",
                    "description": "Retained FRIA documentation.",
                    "evidence_type": "document",
                    "mandatory": True,
                },
                {
                    "requirement_id": "evreq-mitigation-record",
                    "control_id": "ctrl-fria-01",
                    "title": "Mitigation record",
                    "description": "Mitigation documentation.",
                    "evidence_type": "document",
                    "mandatory": True,
                },
            ],
            "records": [{
                "evidence_id": "ev-fria-001",
                "requirement_id": "evreq-fria-record",
                "title": "FRIA record",
                "evidence_type": "document",
                "source_uri": "https://example.org/internal/fria-001",
                "sha256": "a" * 64,
                "collected_at": "2026-09-29T20:00:00+02:00",
                "owner_role": "AI governance",
            }],
        },
    }


def test_workflow_evaluate_exposes_existing_domain_pipeline():
    response = client.post("/workflow/evaluate", json=_workflow_payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {
        "evidence_gap_count": 1,
        "regulatory_impact_count": 1,
        "route_count": 2,
        "human_review_count": 2,
        "log_only_count": 0,
    }
    assert body["evidence_gaps"][0]["requirement_id"] == "evreq-mitigation-record"
    assert body["regulatory_impacts"][0]["control_id"] == "ctrl-fria-01"
    assert {item["reviewer_role"] for item in body["review_routes"]} == {
        "AI governance",
        "Legal",
    }
    assert body["compliance_determination_produced"] is False
    assert response.headers["x-request-id"]


def test_workflow_evaluate_is_deterministic_for_same_payload():
    payload = _workflow_payload()

    first = client.post("/workflow/evaluate", json=payload)
    second = client.post("/workflow/evaluate", json=payload)

    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json()
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_workflow_evaluate_rejects_inconsistent_mapping_as_bad_request():
    payload = _workflow_payload()
    payload["controls"][0]["obligation_id"] = "other-obligation"

    response = client.post("/workflow/evaluate", json=payload)

    assert response.status_code == 400
    assert "obligation does not match mapping" in response.json()["detail"]


def test_workflow_demo_endpoint_is_offline_and_non_compliance():
    response = client.get("/workflow/demo")

    assert response.status_code == 200
    body = response.json()
    assert body["route_count"] == 3
    assert body["human_review_count"] == 2
    assert body["log_only_count"] == 1
    assert body["benchmark"]["routing_accuracy"] == 1.0
    assert body["compliance_determination_produced"] is False



def test_durable_workflow_run_is_idempotent(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    payload = _workflow_payload()

    first = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "fria-run-001"},
    )
    second = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "fria-run-001"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["run_id"] == second.json()["run_id"]
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert len(first.json()["review_cases"]) == 2
    assert len(first.json()["audit_events"]) == 2


def test_durable_workflow_run_rejects_idempotency_key_reuse(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    first = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "fria-run-conflict"},
    )
    changed = _workflow_payload()
    changed["change"]["summary"] = "Different request body."
    second = client.post(
        "/workflow/runs",
        json=changed,
        headers={"Idempotency-Key": "fria-run-conflict"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert "different request" in second.json()["detail"]


def test_durable_workflow_run_can_be_retrieved(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    created = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "fria-run-get"},
    )
    run_id = created.json()["run_id"]

    fetched = client.get(f"/workflow/runs/{run_id}")

    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run_id
    assert fetched.json()["created"] is False
    assert fetched.json()["request_sha256"] == created.json()["request_sha256"]


def test_missing_durable_workflow_run_returns_404(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    response = client.get("/workflow/runs/wf-does-not-exist")

    assert response.status_code == 404


def test_human_yes_response_resolves_persisted_review(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    created = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "fria-human-yes"},
    )
    review = next(
        item
        for item in created.json()["review_cases"]
        if item["subject_type"] == "evidence_gap"
    )

    response = client.post(
        f"/workflow/reviews/{review['review_id']}/responses",
        json={
            "response_id": "resp-evidence-001",
            "answer": "yes",
            "reviewer_role": "AI governance",
            "rationale": "The artefact exists in a separate controlled repository.",
            "responded_at": "2026-09-29T22:30:00+02:00",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["review_case"]["status"] == "resolved"
    assert [item["event_type"] for item in body["audit_events"]] == [
        "review_created",
        "response_recorded",
        "review_closed",
    ]


def test_unknown_response_requires_and_persists_escalation(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    created = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "fria-human-unknown"},
    )
    review = next(
        item
        for item in created.json()["review_cases"]
        if item["subject_type"] == "regulatory_impact"
    )

    invalid = client.post(
        f"/workflow/reviews/{review['review_id']}/responses",
        json={
            "response_id": "resp-impact-invalid",
            "answer": "unknown",
            "reviewer_role": "Legal",
            "rationale": "Interpretive effect remains unresolved.",
            "responded_at": "2026-09-29T22:30:00+02:00",
        },
    )
    assert invalid.status_code == 400
    assert "escalation_target" in invalid.json()["detail"]

    valid = client.post(
        f"/workflow/reviews/{review['review_id']}/responses",
        json={
            "response_id": "resp-impact-001",
            "answer": "unknown",
            "reviewer_role": "Legal",
            "rationale": "Interpretive effect remains unresolved.",
            "responded_at": "2026-09-29T22:31:00+02:00",
            "escalation_target": "Senior Legal",
        },
    )

    assert valid.status_code == 200, valid.text
    assert valid.json()["review_case"]["status"] == "escalated"
    assert valid.json()["review_case"]["escalation"]["target_role"] == "Senior Legal"
    assert [item["event_type"] for item in valid.json()["audit_events"]] == [
        "review_created",
        "response_recorded",
        "escalated",
    ]



def test_persisted_response_rejects_wrong_reviewer_role(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    created = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "fria-wrong-role"},
    )
    review = next(
        item
        for item in created.json()["review_cases"]
        if item["subject_type"] == "evidence_gap"
    )

    response = client.post(
        f"/workflow/reviews/{review['review_id']}/responses",
        json={
            "response_id": "resp-wrong-role",
            "answer": "no",
            "reviewer_role": "Legal",
            "rationale": "Wrong reviewer role should not be accepted.",
            "responded_at": "2026-09-29T22:40:00+02:00",
        },
    )

    assert response.status_code == 400
    assert "assigned review role" in response.json()["detail"]



def test_successful_durable_run_exposes_step_trace(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    response = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "obs-success-001"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert [step["step"] for step in body["steps"]] == [
        "evaluate",
        "persist",
        "review_ready",
    ]
    assert all(step["status"] == "success" for step in body["steps"])
    assert body["failed_step"] is None
    assert body["error_code"] is None


def test_failed_durable_run_is_inspectable(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    payload = _workflow_payload()
    payload["controls"][0]["obligation_id"] = "other-obligation"

    response = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "obs-failed-001"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["failed_step"] == "evaluate"
    assert detail["error_code"] == "domain_validation_failed"
    assert detail["retryable"] is False
    run_id = detail["workflow_run_id"]

    fetched = client.get(f"/workflow/runs/{run_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["status"] == "failed"
    assert body["failed_step"] == "evaluate"
    assert body["error_code"] == "domain_validation_failed"
    assert body["retryable"] is False
    assert len(body["steps"]) == 1
    assert body["steps"][0]["status"] == "failed"


def test_idempotent_replay_does_not_duplicate_step_events(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)
    payload = _workflow_payload()

    first = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "obs-replay-001"},
    )
    second = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "obs-replay-001"},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert len(first.json()["steps"]) == 3
    assert len(second.json()["steps"]) == 3



def test_operational_report_summarizes_persisted_runs(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    payload = _workflow_payload()
    first = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "ops-complete-1"},
    )
    second = client.post(
        "/workflow/runs",
        json=payload,
        headers={"Idempotency-Key": "ops-complete-2"},
    )
    failed_payload = _workflow_payload()
    failed_payload["controls"][0]["obligation_id"] = "other-obligation"
    failed = client.post(
        "/workflow/runs",
        json=failed_payload,
        headers={"Idempotency-Key": "ops-failed-1"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert failed.status_code == 400

    report = client.get("/workflow/operations/report")
    assert report.status_code == 200
    body = report.json()
    assert body["run_count"] == 3
    assert body["completed_count"] == 2
    assert body["failed_count"] == 1
    assert body["running_count"] == 0
    assert body["completion_rate"] == pytest.approx(2 / 3)
    assert body["non_retryable_failure_count"] == 1
    assert body["failure_codes"] == {"domain_validation_failed": 1}
    assert body["step_event_count"] == 7
    assert body["replay_group_count"] == 1
    assert body["replay_consistent_group_count"] == 1
    assert body["replay_consistency"] == 1.0
    assert body["p95_step_ms"] >= 0.0



def test_operator_surface_and_empty_read_models(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    page = client.get("/operator")
    assert page.status_code == 200
    assert "MAILO RegAI Operator" in page.text
    assert "Regulatory Changes" in page.text
    assert "Review Queue" in page.text
    assert "Case Trace" in page.text

    assert client.get("/operator/api/changes").json() == []
    assert client.get("/operator/api/reviews").json() == []


def test_operator_views_expose_change_reviews_and_case_trace(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    created = client.post(
        "/workflow/runs",
        json=_workflow_payload(),
        headers={"Idempotency-Key": "operator-001"},
    )
    assert created.status_code == 201
    run_id = created.json()["run_id"]

    changes = client.get("/operator/api/changes")
    assert changes.status_code == 200
    assert changes.json() == [{
        "change_id": "ai-act-2026-art-27-4-changed",
        "run_count": 1,
        "latest_run_id": run_id,
        "latest_status": "completed",
        "latest_created_at": created.json()["created_at"],
        "failed_run_count": 0,
    }]

    reviews = client.get("/operator/api/reviews")
    assert reviews.status_code == 200
    assert len(reviews.json()) == 2
    assert {item["reviewer_role"] for item in reviews.json()} == {
        "AI governance",
        "Legal",
    }

    trace = client.get(f"/operator/api/cases/{run_id}")
    assert trace.status_code == 200
    body = trace.json()
    assert body["run"]["run_id"] == run_id
    assert body["run"]["change_id"] == "ai-act-2026-art-27-4-changed"
    assert [step["step"] for step in body["steps"]] == [
        "evaluate",
        "persist",
        "review_ready",
    ]
    assert len(body["reviews"]) == 2
    assert len(body["audit_events"]) == 2
    assert body["compliance_determination_produced"] is False


def test_operator_case_trace_missing_run_returns_404(tmp_path, monkeypatch):
    repository = SQLiteWorkflowRepository(tmp_path / "workflow.db")
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", repository)

    response = client.get("/operator/api/cases/wf-missing")

    assert response.status_code == 404
