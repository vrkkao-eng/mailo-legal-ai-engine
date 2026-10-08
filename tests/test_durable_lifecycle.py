"""In-process companion to the Docker container-replacement acceptance."""

from copy import deepcopy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from mailo_cli import api
from mailo_cli.regulatory.persistence import SQLiteWorkflowRepository


FIXTURE = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "workflow_lifecycle.json"


def test_durable_lifecycle_survives_repository_reopen(tmp_path, monkeypatch):
    """A new repository object must read exactly the same persisted operator state."""
    database = tmp_path / "workflow.db"
    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", SQLiteWorkflowRepository(database))
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    client = TestClient(api.app)
    headers = {"Idempotency-Key": "synthetic-lifecycle"}

    created = client.post("/workflow/runs", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    run_id = body["run_id"]
    assert body["status"] == "completed"
    assert len(body["review_cases"]) == len(body["audit_events"]) == 2

    replay = client.post("/workflow/runs", json=payload, headers=headers)
    assert replay.status_code == 200, replay.text
    assert replay.json()["run_id"] == run_id
    assert replay.json()["created"] is False
    assert replay.json()["review_cases"] == body["review_cases"]
    assert replay.json()["audit_events"] == body["audit_events"]
    assert replay.json()["steps"] == body["steps"]

    changed = deepcopy(payload)
    changed["change"]["summary"] = "Different synthetic request body."
    conflict = client.post("/workflow/runs", json=changed, headers=headers)
    assert conflict.status_code == 409, conflict.text
    changes_before_failure = client.get("/operator/api/changes")
    assert changes_before_failure.status_code == 200
    matching = [
        item for item in changes_before_failure.json()
        if item["change_id"] == payload["change"]["change_id"]
    ]
    assert len(matching) == 1
    assert matching[0]["run_count"] == 1

    failed_payload = deepcopy(payload)
    failed_payload["controls"][0]["obligation_id"] = "other-obligation"
    failed = client.post(
        "/workflow/runs", json=failed_payload,
        headers={"Idempotency-Key": "synthetic-lifecycle-failed"},
    )
    assert failed.status_code == 400, failed.text
    failed_id = failed.json()["detail"]["workflow_run_id"]

    paths = {
        "run": f"/workflow/runs/{run_id}",
        "trace": f"/operator/api/cases/{run_id}",
        "queue": "/operator/api/reviews",
        "changes": "/operator/api/changes",
        "failed_run": f"/workflow/runs/{failed_id}",
        "operations": "/workflow/operations/report",
    }

    def snapshot():
        responses = {name: client.get(path) for name, path in paths.items()}
        assert all(response.status_code == 200 for response in responses.values())
        return {name: response.json() for name, response in responses.items()}

    before = snapshot()
    assert before["failed_run"]["status"] == "failed"
    assert before["operations"]["run_count"] == 2
    assert before["operations"]["failed_count"] == 1
    assert before["trace"]["compliance_determination_produced"] is False
    review_ids = {item["review_id"] for item in body["review_cases"]}
    audit_ids = {item["event_id"] for item in body["audit_events"]}
    assert {item["review_id"] for item in before["trace"]["reviews"]} == review_ids
    assert {item["event_id"] for item in before["trace"]["audit_events"]} == audit_ids
    assert {
        item["review_id"] for item in before["queue"] if item["run_id"] == run_id
    } == review_ids

    monkeypatch.setattr(api, "_WORKFLOW_REPOSITORY", SQLiteWorkflowRepository(database))
    assert snapshot() == before
    replay_after = client.post("/workflow/runs", json=payload, headers=headers)
    assert replay_after.status_code == 200, replay_after.text
    assert replay_after.json()["run_id"] == run_id
    assert replay_after.json()["created"] is False
    assert snapshot() == before
