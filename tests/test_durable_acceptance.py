"""Failure evidence must stay trustworthy even when Docker cannot complete."""

import http.client
import json
import subprocess
import sys
from unittest.mock import Mock

import pytest

from tools import durable_acceptance as acceptance


@pytest.fixture
def report_path(tmp_path, monkeypatch):
    path = tmp_path / "acceptance.json"
    # Reusing a report path must never preserve this old success on failure.
    path.write_text('{"status": "passed", "old_run": true}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["acceptance", "--report", str(path)])
    monkeypatch.setattr(acceptance, "choose_port", lambda port: 12000)
    monkeypatch.setattr(acceptance, "source_identity", lambda: {"head_commit": "test"})
    return path


@pytest.mark.parametrize("failure", ["port", "missing_fixture", "invalid_fixture", "git"])
def test_preflight_failure_replaces_old_success(report_path, monkeypatch, tmp_path, failure):
    lifecycle = Mock()
    monkeypatch.setattr(acceptance.Acceptance, "lifecycle", lifecycle)
    if failure == "port":
        error = OSError("port already in use")
        monkeypatch.setattr(acceptance, "choose_port", Mock(side_effect=error))
    elif failure == "git":
        error = subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"])
        monkeypatch.setattr(acceptance, "source_identity", Mock(side_effect=error))
    else:
        fixture = tmp_path / "fixture.json"
        if failure == "invalid_fixture":
            fixture.write_text("{", encoding="utf-8")
        monkeypatch.setattr(acceptance, "FIXTURE", fixture)

    assert acceptance.main() == 1
    lifecycle.assert_not_called()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"]
    assert report["cleanup"] == "not_needed"
    assert report["checks"] == []
    assert "finished_at_utc" in report
    assert "old_run" not in report


@pytest.mark.parametrize("error", [
    http.client.IncompleteRead(b"partial", 50),
    http.client.BadStatusLine("invalid status"),
])
def test_http_protocol_failure_is_reported(report_path, monkeypatch, error):
    monkeypatch.setattr(acceptance.Acceptance, "lifecycle", Mock(side_effect=error))

    assert acceptance.main() == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["error"].startswith(type(error).__name__ + ":")
    assert report["cleanup"] == "not_needed"


def test_cleanup_inspect_timeout_finishes_with_failed_evidence(report_path, monkeypatch):
    def completed_lifecycle(runner):
        runner.attempted_start = True

    def timed_out_inspect(command, **kwargs):
        assert command[:3] == ["docker", "volume", "inspect"]
        assert kwargs["timeout"] == 30
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(acceptance.Acceptance, "lifecycle", completed_lifecycle)
    monkeypatch.setattr(acceptance.subprocess, "run", timed_out_inspect)
    compose = Mock()
    monkeypatch.setattr(acceptance.Acceptance, "compose", compose)

    assert acceptance.main() == 1
    compose.assert_not_called()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["cleanup"] == "failed"
    assert report["cleanup_error"].startswith("TimeoutExpired:")
    assert "finished_at_utc" in report
