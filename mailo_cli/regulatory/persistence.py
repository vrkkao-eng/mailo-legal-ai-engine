"""SQLite transactional persistence for durable RegAI workflow runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .evidence import EvidenceRecord
from .review import ReviewDisposition
from .service import WorkflowEvaluationResult
from .observability import WorkflowErrorCode, WorkflowStepEvent


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused with a different request."""


class WorkflowRunNotFound(LookupError):
    """Raised when a durable workflow run does not exist."""


@dataclass(frozen=True, slots=True)
class PersistedWorkflowRun:
    run_id: str
    idempotency_key: str
    request_sha256: str
    change_id: str
    status: str
    created_at: datetime
    request_payload: dict[str, Any]
    result_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "idempotency_key": self.idempotency_key,
            "request_sha256": self.request_sha256,
            "change_id": self.change_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "request": self.request_payload,
            "result": self.result_payload,
        }


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _request_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _review_id(run_id: str, subject_id: str) -> str:
    digest = hashlib.sha256(subject_id.encode("utf-8")).hexdigest()[:16]
    return f"review:{run_id}:{digest}"


class SQLiteWorkflowRepository:
    """Transactional repository for workflow runs and review/audit state."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_sha256 TEXT NOT NULL,
                    change_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    failed_step TEXT,
                    error_code TEXT,
                    retryable INTEGER,
                    error_detail TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_steps (
                    run_id TEXT NOT NULL,
                    step_sequence INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    detail TEXT NOT NULL,
                    error_code TEXT,
                    retryable INTEGER,
                    PRIMARY KEY (run_id, step_sequence),
                    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS evidence_records (
                    run_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    requirement_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    owner_role TEXT NOT NULL,
                    PRIMARY KEY (run_id, evidence_id),
                    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS review_cases (
                    review_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    question_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (run_id, subject_id),
                    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS human_responses (
                    response_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    responded_at TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES review_cases(review_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS escalations (
                    escalation_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL UNIQUE,
                    target_role TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    escalated_at TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES review_cases(review_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL,
                    event_sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES review_cases(review_id) ON DELETE CASCADE
                );
                """
            )

    def reserve_run(
        self,
        *,
        idempotency_key: str,
        request_payload: dict[str, Any],
        change_id: str,
    ) -> tuple[PersistedWorkflowRun, bool]:
        """Reserve a durable workflow run before evaluation begins."""

        key = idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key must not be empty")
        if len(key) > 128:
            raise ValueError("idempotency_key must not exceed 128 characters")

        request_hash = _request_sha256(request_payload)
        created_at = datetime.now(timezone.utc)
        run_id = f"wf-{uuid.uuid4()}"

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM workflow_runs WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing is not None:
                if existing["request_sha256"] != request_hash:
                    raise IdempotencyConflict(
                        "idempotency key was already used with a different request"
                    )
                connection.rollback()
                return self._row_to_run(existing), False

            connection.execute(
                """
                INSERT INTO workflow_runs (
                    run_id, idempotency_key, request_sha256, change_id, status,
                    created_at, request_json, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    key,
                    request_hash,
                    change_id,
                    "running",
                    created_at.isoformat(),
                    _canonical_json(request_payload),
                    _canonical_json({}),
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return self.get_run(run_id), True

    def append_step(self, run_id: str, event: WorkflowStepEvent) -> None:
        """Append one ordered operational step event."""

        self.get_run(run_id)
        with self._connect() as connection:
            next_sequence = connection.execute(
                "SELECT COALESCE(MAX(step_sequence), -1) + 1 FROM workflow_steps WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO workflow_steps (
                    run_id, step_sequence, step, status, duration_ms, detail,
                    error_code, retryable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    next_sequence,
                    event.step.value,
                    event.status.value,
                    event.duration_ms,
                    event.detail,
                    event.error_code.value if event.error_code else None,
                    None if event.retryable is None else int(event.retryable),
                ),
            )

    def list_steps(self, run_id: str) -> tuple[dict[str, Any], ...]:
        self.get_run(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT step_sequence, step, status, duration_ms, detail,
                       error_code, retryable
                FROM workflow_steps
                WHERE run_id = ?
                ORDER BY step_sequence
                """,
                (run_id,),
            ).fetchall()
        return tuple(
            {
                "sequence": row["step_sequence"],
                "step": row["step"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "detail": row["detail"],
                "error_code": row["error_code"],
                "retryable": (
                    None if row["retryable"] is None else bool(row["retryable"])
                ),
            }
            for row in rows
        )

    def mark_failed(
        self,
        run_id: str,
        *,
        failed_step: str,
        error_code: WorkflowErrorCode,
        retryable: bool,
        detail: str,
    ) -> PersistedWorkflowRun:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE workflow_runs
                SET status = 'failed', failed_step = ?, error_code = ?,
                    retryable = ?, error_detail = ?
                WHERE run_id = ?
                """,
                (
                    failed_step,
                    error_code.value,
                    int(retryable),
                    detail,
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise WorkflowRunNotFound(f"workflow run not found: {run_id}")
        return self.get_run(run_id)

    def finalize_run(
        self,
        run_id: str,
        *,
        result: WorkflowEvaluationResult,
        evidence_records: Iterable[EvidenceRecord],
    ) -> PersistedWorkflowRun:
        """Persist evaluation output, review cases and audit events atomically."""

        result_payload = result.to_dict()
        records = tuple(evidence_records)
        created_at = self.get_run(run_id).created_at

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise WorkflowRunNotFound(f"workflow run not found: {run_id}")
            if row["status"] != "running":
                raise ValueError("workflow run is not in running state")

            connection.execute(
                "UPDATE workflow_runs SET result_json = ?, status = 'completed' WHERE run_id = ?",
                (_canonical_json(result_payload), run_id),
            )

            for record in records:
                connection.execute(
                    """
                    INSERT INTO evidence_records (
                        run_id, evidence_id, requirement_id, evidence_type,
                        source_uri, sha256, collected_at, owner_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        record.evidence_id,
                        record.requirement_id,
                        record.evidence_type.value,
                        record.source_uri,
                        record.sha256,
                        record.collected_at.isoformat(),
                        record.owner_role,
                    ),
                )

            for route in result.review_routes:
                if route.disposition is not ReviewDisposition.HUMAN_REVIEW:
                    continue
                if route.question is None or route.reviewer_role is None:
                    raise ValueError("human review route is missing question or reviewer role")
                review_id = _review_id(run_id, route.subject_id)
                question_json = _canonical_json(
                    {
                        "question_id": route.question.question_id,
                        "prompt": route.question.prompt,
                        "permitted_answers": [
                            answer.value for answer in route.question.permitted_answers
                        ],
                        "context_refs": list(route.question.context_refs),
                    }
                )
                connection.execute(
                    """
                    INSERT INTO review_cases (
                        review_id, run_id, subject_type, subject_id, reviewer_role,
                        status, question_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        run_id,
                        route.subject_type.value,
                        route.subject_id,
                        route.reviewer_role,
                        "open",
                        question_json,
                        created_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, review_id, event_sequence, event_type,
                        actor_role, occurred_at, detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"evt:{review_id}:created",
                        review_id,
                        0,
                        "review_created",
                        "system",
                        created_at.isoformat(),
                        "Durable review case created from workflow evaluation.",
                    ),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return self.get_run(run_id)

    def create_run(
        self,
        *,
        idempotency_key: str,
        request_payload: dict[str, Any],
        change_id: str,
        result: WorkflowEvaluationResult,
        evidence_records: Iterable[EvidenceRecord],
    ) -> tuple[PersistedWorkflowRun, bool]:
        """Persist a workflow snapshot atomically.

        Returns a pair of persisted run and created flag. Replaying the same
        idempotency key with the same request returns the original run; a
        different request conflicts.
        """

        key = idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key must not be empty")
        if len(key) > 128:
            raise ValueError("idempotency_key must not exceed 128 characters")

        request_hash = _request_sha256(request_payload)
        created_at = datetime.now(timezone.utc)
        result_payload = result.to_dict()
        run_id = f"wf-{uuid.uuid4()}"
        records = tuple(evidence_records)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM workflow_runs WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing is not None:
                if existing["request_sha256"] != request_hash:
                    raise IdempotencyConflict(
                        "idempotency key was already used with a different request"
                    )
                connection.rollback()
                return self._row_to_run(existing), False

            connection.execute(
                """
                INSERT INTO workflow_runs (
                    run_id, idempotency_key, request_sha256, change_id, status,
                    created_at, request_json, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    key,
                    request_hash,
                    change_id,
                    "completed",
                    created_at.isoformat(),
                    _canonical_json(request_payload),
                    _canonical_json(result_payload),
                ),
            )

            for record in records:
                connection.execute(
                    """
                    INSERT INTO evidence_records (
                        run_id, evidence_id, requirement_id, evidence_type,
                        source_uri, sha256, collected_at, owner_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        record.evidence_id,
                        record.requirement_id,
                        record.evidence_type.value,
                        record.source_uri,
                        record.sha256,
                        record.collected_at.isoformat(),
                        record.owner_role,
                    ),
                )

            for route in result.review_routes:
                if route.disposition is not ReviewDisposition.HUMAN_REVIEW:
                    continue
                if route.question is None or route.reviewer_role is None:
                    raise ValueError("human review route is missing question or reviewer role")
                review_id = _review_id(run_id, route.subject_id)
                question_json = _canonical_json(
                    {
                        "question_id": route.question.question_id,
                        "prompt": route.question.prompt,
                        "permitted_answers": [
                            answer.value for answer in route.question.permitted_answers
                        ],
                        "context_refs": list(route.question.context_refs),
                    }
                )
                connection.execute(
                    """
                    INSERT INTO review_cases (
                        review_id, run_id, subject_type, subject_id, reviewer_role,
                        status, question_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        run_id,
                        route.subject_type.value,
                        route.subject_id,
                        route.reviewer_role,
                        "open",
                        question_json,
                        created_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, review_id, event_sequence, event_type,
                        actor_role, occurred_at, detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"evt:{review_id}:created",
                        review_id,
                        0,
                        "review_created",
                        "system",
                        created_at.isoformat(),
                        "Durable review case created from workflow evaluation.",
                    ),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return self.get_run(run_id), True

    def get_run(self, run_id: str) -> PersistedWorkflowRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise WorkflowRunNotFound(f"workflow run not found: {run_id}")
        return self._row_to_run(row)

    def list_review_cases(self, run_id: str) -> tuple[dict[str, Any], ...]:
        self.get_run(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT review_id, subject_type, subject_id, reviewer_role, status,
                       question_json, created_at
                FROM review_cases
                WHERE run_id = ?
                ORDER BY review_id
                """,
                (run_id,),
            ).fetchall()
        return tuple(
            {
                "review_id": row["review_id"],
                "run_id": run_id,
                "subject_type": row["subject_type"],
                "subject_id": row["subject_id"],
                "reviewer_role": row["reviewer_role"],
                "status": row["status"],
                "question": json.loads(row["question_json"]),
                "created_at": row["created_at"],
                "escalation": self.get_escalation(row["review_id"]),
            }
            for row in rows
        )

    def get_review_case(self, review_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT review_id, run_id, subject_type, subject_id, reviewer_role,
                       status, question_json, created_at
                FROM review_cases
                WHERE review_id = ?
                """,
                (review_id,),
            ).fetchone()
        if row is None:
            raise WorkflowRunNotFound(f"review case not found: {review_id}")
        return {
            "review_id": row["review_id"],
            "run_id": row["run_id"],
            "subject_type": row["subject_type"],
            "subject_id": row["subject_id"],
            "reviewer_role": row["reviewer_role"],
            "status": row["status"],
            "question": json.loads(row["question_json"]),
            "created_at": row["created_at"],
            "escalation": self.get_escalation(review_id),
        }

    def get_escalation(self, review_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT escalation_id, review_id, target_role, reason, escalated_at
                FROM escalations
                WHERE review_id = ?
                """,
                (review_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def record_response(
        self,
        *,
        review_id: str,
        response_id: str,
        answer: str,
        reviewer_role: str,
        rationale: str,
        responded_at: datetime,
        escalation_target: str | None = None,
    ) -> dict[str, Any]:
        """Persist a human response and terminal review transition atomically."""

        if answer not in {"yes", "no", "unknown"}:
            raise ValueError("answer must be yes, no, or unknown")
        if responded_at.tzinfo is None or responded_at.utcoffset() is None:
            raise ValueError("responded_at must include a timezone offset")
        if not response_id.strip():
            raise ValueError("response_id must not be empty")
        if not reviewer_role.strip():
            raise ValueError("reviewer_role must not be empty")
        if not rationale.strip():
            raise ValueError("rationale must not be empty")
        if answer == "unknown" and not (escalation_target or "").strip():
            raise ValueError("UNKNOWN response requires escalation_target")
        if answer != "unknown" and escalation_target is not None:
            raise ValueError("escalation_target is only valid for UNKNOWN responses")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            case = connection.execute(
                "SELECT * FROM review_cases WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            if case is None:
                raise WorkflowRunNotFound(f"review case not found: {review_id}")
            if case["status"] not in {"open", "in_review"}:
                raise ValueError("review case is already terminal")
            if reviewer_role.strip() != case["reviewer_role"]:
                raise ValueError("reviewer_role does not match assigned review role")

            existing = connection.execute(
                "SELECT * FROM human_responses WHERE response_id = ?",
                (response_id,),
            ).fetchone()
            if existing is not None:
                raise ValueError(f"duplicate response_id: {response_id}")

            connection.execute(
                """
                INSERT INTO human_responses (
                    response_id, review_id, answer, reviewer_role, rationale, responded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    response_id,
                    review_id,
                    answer,
                    reviewer_role.strip(),
                    rationale.strip(),
                    responded_at.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, review_id, event_sequence, event_type,
                    actor_role, occurred_at, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt:{review_id}:{response_id}:response",
                    review_id,
                    1,
                    "response_recorded",
                    reviewer_role.strip(),
                    responded_at.isoformat(),
                    "Human response recorded.",
                ),
            )

            if answer == "unknown":
                status = "escalated"
                connection.execute(
                    """
                    INSERT INTO escalations (
                        escalation_id, review_id, target_role, reason, escalated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        f"esc:{review_id}:{response_id}",
                        review_id,
                        escalation_target.strip(),
                        rationale.strip(),
                        responded_at.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, review_id, event_sequence, event_type,
                        actor_role, occurred_at, detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"evt:{review_id}:{response_id}:escalated",
                        review_id,
                        2,
                        "escalated",
                        reviewer_role.strip(),
                        responded_at.isoformat(),
                        f"Escalated to {escalation_target.strip()}.",
                    ),
                )
            else:
                status = "resolved"
                connection.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, review_id, event_sequence, event_type,
                        actor_role, occurred_at, detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"evt:{review_id}:{response_id}:closed",
                        review_id,
                        2,
                        "review_closed",
                        reviewer_role.strip(),
                        responded_at.isoformat(),
                        "Review case closed after focused human response.",
                    ),
                )

            connection.execute(
                "UPDATE review_cases SET status = ? WHERE review_id = ?",
                (status, review_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return self.get_review_case(review_id)

    def list_audit_events(self, run_id: str) -> tuple[dict[str, Any], ...]:
        self.get_run(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.event_id, a.review_id, a.event_type, a.actor_role,
                       a.occurred_at, a.detail
                FROM audit_events AS a
                JOIN review_cases AS r ON r.review_id = a.review_id
                WHERE r.run_id = ?
                ORDER BY a.occurred_at, a.event_sequence, a.event_id
                """,
                (run_id,),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def _row_to_run(self, row: sqlite3.Row) -> PersistedWorkflowRun:
        return PersistedWorkflowRun(
            run_id=row["run_id"],
            idempotency_key=row["idempotency_key"],
            request_sha256=row["request_sha256"],
            change_id=row["change_id"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            request_payload=json.loads(row["request_json"]),
            result_payload=json.loads(row["result_json"]),
        )
