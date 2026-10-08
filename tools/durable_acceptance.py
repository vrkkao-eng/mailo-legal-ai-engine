"""Black-box, disposable Docker acceptance for the durable workflow lifecycle.

Uses only the bundled synthetic fixture, loopback HTTP, and a uniquely named
Compose project. The script creates and removes only its own Docker resources.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tools" / "fixtures" / "workflow_lifecycle.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def new_report() -> dict[str, object]:
    return {
        "status": "running", "started_at_utc": utc_now(),
        "scope": "Synthetic local durable workflow and container replacement; no legal-quality or cloud claim",
        "checks": [], "commands": [], "cleanup": "not_needed",
    }


def source_identity() -> dict[str, object]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode().strip()
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, check=True,
    ).stdout
    paths = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    digest = hashlib.sha256()
    for raw_path in sorted(set(paths.split(b"\0")) - {b""}):
        path = ROOT / os.fsdecode(raw_path)
        if not path.is_file():
            continue
        digest.update(raw_path + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {"head_commit": head, "working_tree_dirty": bool(status),
            "source_tree_sha256": digest.hexdigest()}


def choose_port(requested: int | None) -> int:
    if requested is not None:
        ensure(1024 <= requested <= 65535, "Host port must be between 1024 and 65535")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", requested or 0))
        return probe.getsockname()[1]


class Acceptance:
    def __init__(self, port: int, payload: dict, fixture_sha256: str):
        self.port = port
        self.payload = payload
        self.project = "mailo-accept-" + uuid4().hex[:12]
        self.environment = dict(os.environ)
        # Caller environment must not silently redirect the disposable database.
        for name in ("MAILO_WORKFLOW_DB", "MAILO_MAX_REQUEST_BYTES",
                     "MAILO_REQUEST_TIMEOUT_SECONDS", "MAILO_CORS_ORIGINS"):
            self.environment.pop(name, None)
        self.environment["MAILO_HOST_PORT"] = str(port)
        self.attempted_start = False
        self.report = new_report()
        self.report.update({
            "project": self.project, "loopback_port": port,
            "fixture": str(FIXTURE.relative_to(ROOT)), "fixture_sha256": fixture_sha256,
            "source": source_identity(),
        })

    def command(self, args: list[str], *, timeout: int = 120) -> str:
        self.report["commands"].append(args)
        result = subprocess.run(
            args, cwd=ROOT, env=self.environment, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()[-1600:]
            raise RuntimeError(f"Command failed ({result.returncode}): {args[0]} {args[1:4]}: {detail}")
        return result.stdout.strip()

    def compose(self, *args: str, timeout: int = 120) -> str:
        return self.command(
            ["docker", "compose", "-p", self.project, "--env-file", ".env.example",
             "-f", "compose.yaml", *args], timeout=timeout,
        )

    def no_preexisting_resources(self) -> None:
        for noun in ("ps", "volume", "network"):
            if noun == "ps":
                args = ["docker", "ps", "-a", "--filter",
                        f"label=com.docker.compose.project={self.project}", "-q"]
            else:
                args = ["docker", noun, "ls", "--filter",
                        f"label=com.docker.compose.project={self.project}", "-q"]
            ensure(not self.command(args), f"Project {self.project} already has {noun} resources")

    def volume(self) -> dict:
        name = self.project + "_mailo-data"
        data = json.loads(self.command(["docker", "volume", "inspect", name]))[0]
        ensure(data["Name"] == name, "Unexpected volume name")
        ensure(data.get("Labels", {}).get("com.docker.compose.project") == self.project,
               "Volume does not belong to this acceptance project")
        return {"name": data["Name"], "created_at": data["CreatedAt"]}

    def container_id(self) -> str:
        value = self.compose("ps", "-q", "api")
        ensure(bool(value), "API container was not found")
        return value

    def request(self, name: str, method: str, path: str, *, expected: int = 200,
                body: dict | None = None, key: str | None = None) -> dict | list:
        started = time.perf_counter()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        headers = {}
        encoded = None
        if body is not None:
            encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["Idempotency-Key"] = key
        try:
            connection.request(method, path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            duration = round((time.perf_counter() - started) * 1000, 3)
            data = json.loads(raw)
            request_id = response.getheader("X-Request-ID")
            passed = response.status == expected and bool(request_id)
            self.report["checks"].append({
                "name": name, "status": response.status, "expected_status": expected,
                "duration_ms": duration, "request_id": request_id, "passed": passed,
            })
            ensure(passed, f"{name}: expected {expected} with request ID; got {response.status}")
            return data
        finally:
            connection.close()

    def wait_ready(self, stage: str) -> None:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
                try:
                    connection.request("GET", "/health")
                    response = connection.getresponse()
                    response.read()
                    if response.status == 200:
                        self.request(stage + "_health", "GET", "/health")
                        self.request(stage + "_ready", "GET", "/ready")
                        return
                finally:
                    connection.close()
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(1)
        raise TimeoutError(f"Service did not become healthy after {stage}")

    def runtime_identity(self) -> None:
        code = (
            "import json, os, sys, mailo_cli; "
            "from importlib.metadata import version; "
            "print(json.dumps({'python':sys.version.split()[0], 'uid':os.getuid(), "
            "'gid':os.getgid(), 'package_path':mailo_cli.__file__, "
            "'database':os.environ['MAILO_WORKFLOW_DB'], "
            "'versions':{name:version(name) for name in "
            "('mailo-legal-ai-engine','fastapi','starlette','rdflib','pyshacl')}}))"
        )
        value = json.loads(self.compose("exec", "-T", "api", "python", "-c", code))
        ensure(value["uid"] == 10001 and value["gid"] == 10001, "Runtime is not UID/GID 10001")
        ensure(value["database"] == "/data/workflow.db", "Database is not on the named volume")
        ensure("/site-packages/" in value["package_path"], "Runtime is not using installed wheel")
        self.report["runtime"] = value
        image = self.command(["docker", "image", "inspect", self.project + "-api",
                              "--format", "{{.Id}}"])
        self.report["image_id"] = image

    def lifecycle(self) -> None:
        self.no_preexisting_resources()
        self.attempted_start = True
        self.report["cleanup"] = "pending"
        print("Building and starting disposable service...", file=sys.stderr, flush=True)
        self.compose("up", "--detach", "--build", "api", timeout=600)
        first_container = self.container_id()
        first_volume = self.volume()
        self.wait_ready("before")
        self.runtime_identity()

        key = "acceptance-" + self.project
        create = self.request("create_run", "POST", "/workflow/runs", expected=201,
                              body=self.payload, key=key)
        ensure(create["status"] == "completed" and create["created"] is True,
               "Expected a newly completed run")
        run_id = create["run_id"]
        ensure(len(create["review_cases"]) == 2 and len(create["audit_events"]) == 2,
               "Synthetic FRIA fixture should produce two reviews and two audit events")
        replay = self.request("replay_before", "POST", "/workflow/runs",
                              body=self.payload, key=key)
        ensure(replay["run_id"] == run_id and replay["created"] is False,
               "Same-key replay did not return the original run")
        ensure(replay["review_cases"] == create["review_cases"]
               and replay["audit_events"] == create["audit_events"]
               and replay["steps"] == create["steps"],
               "Same-key replay added review, audit, or step records")

        changed = deepcopy(self.payload)
        changed["change"]["summary"] = "Different synthetic request body."
        conflict = self.request("conflicting_key", "POST", "/workflow/runs",
                                expected=409, body=changed, key=key)
        ensure("different request" in conflict["detail"], "Expected idempotency conflict")
        changes_before_failure = self.request("changes_before_failure", "GET",
                                               "/operator/api/changes")
        matching = [item for item in changes_before_failure
                    if item["change_id"] == self.payload["change"]["change_id"]]
        ensure(len(matching) == 1 and matching[0]["run_count"] == 1,
               "Replay or conflict created a duplicate durable run")

        failed_payload = deepcopy(self.payload)
        failed_payload["controls"][0]["obligation_id"] = "other-obligation"
        failed_response = self.request(
            "create_failed_run", "POST", "/workflow/runs", expected=400,
            body=failed_payload, key=key + "-failed",
        )
        detail = failed_response["detail"]
        failed_id = detail["workflow_run_id"]
        ensure(failed_id != run_id and detail["failed_step"] == "evaluate"
               and detail["error_code"] == "domain_validation_failed"
               and detail["retryable"] is False,
               "Failed-run error did not expose its durable identity and taxonomy")

        paths = {
            "run": f"/workflow/runs/{run_id}",
            "trace": f"/operator/api/cases/{run_id}",
            "queue": "/operator/api/reviews",
            "changes": "/operator/api/changes",
            "failed_run": f"/workflow/runs/{failed_id}",
            "operations": "/workflow/operations/report",
        }

        def snapshot(stage: str) -> dict:
            return {name: self.request(f"{stage}_{name}", "GET", path)
                    for name, path in paths.items()}

        before = snapshot("before")
        ensure(before["run"]["run_id"] == run_id
               and before["run"]["status"] == "completed", "Original run could not be read")
        ensure(before["failed_run"]["status"] == "failed"
               and before["failed_run"]["error_code"] == "domain_validation_failed"
               and len(before["failed_run"]["steps"]) == 1,
               "Failed run was not inspectable")
        review_ids = {item["review_id"] for item in create["review_cases"]}
        audit_ids = {item["event_id"] for item in create["audit_events"]}
        ensure({item["review_id"] for item in before["trace"]["reviews"]} == review_ids,
               "Case trace reviews do not match the durable run")
        ensure({item["event_id"] for item in before["trace"]["audit_events"]} == audit_ids,
               "Case trace audit events do not match the durable run")
        ensure({item["review_id"] for item in before["queue"]
                if item["run_id"] == run_id} == review_ids,
               "Review queue does not contain the durable run's cases")
        ensure(before["operations"]["run_count"] == 2
               and before["operations"]["failed_count"] == 1,
               "Operational report does not reflect completed and failed runs")
        ensure(before["trace"]["compliance_determination_produced"] is False,
               "Operator trace overstated the legal boundary")

        print("Replacing container while retaining the test volume...",
              file=sys.stderr, flush=True)
        restart_started = time.perf_counter()
        self.compose("stop", "api")
        self.compose("up", "--detach", "--no-build", "--force-recreate", "api")
        self.wait_ready("after")
        restart_ms = round((time.perf_counter() - restart_started) * 1000, 3)
        second_container = self.container_id()
        second_volume = self.volume()
        ensure(first_container != second_container, "Container was not replaced")
        ensure(first_volume == second_volume, "Test volume was not preserved")
        after = snapshot("after")
        ensure(after == before, "Persisted run, failure, queue, trace, or operations changed")
        replay_after = self.request("replay_after", "POST", "/workflow/runs",
                                    body=self.payload, key=key)
        ensure(replay_after["run_id"] == run_id and replay_after["created"] is False,
               "Post-restart replay did not preserve the original run ID")
        ensure(replay_after["review_cases"] == create["review_cases"]
               and replay_after["audit_events"] == create["audit_events"]
               and replay_after["steps"] == create["steps"],
               "Post-restart replay duplicated a review, audit, or step record")
        ensure(snapshot("after_replay") == before,
               "Post-restart replay changed the persisted operator snapshot")

        durations = sorted(item["duration_ms"] for item in self.report["checks"])
        self.report["observations"] = {
            "run_id": run_id, "failed_run_id": failed_id,
            "request_sha256": create["request_sha256"],
            "review_ids": sorted(review_ids), "audit_event_ids": sorted(audit_ids),
            "initial_container_id": first_container,
            "replacement_container_id": second_container,
            "preserved_volume": first_volume,
            "container_replace_ms": restart_ms,
            "observed_http_latency_ms": {
                "count": len(durations), "mean": round(statistics.mean(durations), 3),
                "p50": round(statistics.median(durations), 3),
                "p95_nearest_rank": durations[(95 * len(durations) + 99) // 100 - 1],
            },
        }
        self.report["snapshots"] = {"before_replacement": before,
                                    "after_replacement": after}

    def cleanup(self) -> None:
        if not self.attempted_start:
            self.report["cleanup"] = "not_needed"
            return
        # The UUID project was checked empty before creation. Verify the named
        # volume label again before using Compose's project-scoped --volumes.
        name = self.project + "_mailo-data"
        lookup = subprocess.run(
            ["docker", "volume", "inspect", name], cwd=ROOT, env=self.environment,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        if lookup.returncode == 0:
            data = json.loads(lookup.stdout)[0]
            ensure(data.get("Labels", {}).get("com.docker.compose.project") == self.project,
                   "Refusing cleanup: volume project label changed")
        self.compose("down", "--volumes", timeout=120)
        self.report["cleanup"] = "own_test_project_removed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write JSON evidence to this path")
    parser.add_argument("--port", type=int, help="Loopback host port; default chooses a free port")
    args = parser.parse_args()
    report = new_report()
    acceptance = None
    try:
        fixture_bytes = FIXTURE.read_bytes()
        payload = json.loads(fixture_bytes)
        acceptance = Acceptance(
            choose_port(args.port), payload, hashlib.sha256(fixture_bytes).hexdigest(),
        )
        report = acceptance.report
        acceptance.lifecycle()
        report["status"] = "passed"
    except (AssertionError, RuntimeError, OSError, ValueError, KeyError,
            http.client.HTTPException, subprocess.SubprocessError) as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            if acceptance is not None:
                acceptance.cleanup()
        except (AssertionError, RuntimeError, OSError, ValueError,
                subprocess.SubprocessError) as exc:
            report["status"] = "failed"
            report["cleanup"] = "failed"
            report["cleanup_error"] = f"{type(exc).__name__}: {exc}"
        report["finished_at_utc"] = utc_now()
        output = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output, encoding="utf-8")
        print(output)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
