"""Read models for the minimal RegAI operator surface."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .persistence import SQLiteWorkflowRepository, WorkflowRunNotFound


def regulatory_changes_view(
    repository: SQLiteWorkflowRepository,
) -> tuple[dict[str, Any], ...]:
    """Aggregate durable runs by regulatory change for operator browsing."""

    grouped: dict[str, list] = defaultdict(list)
    for run in repository.list_runs():
        grouped[run.change_id].append(run)

    items: list[dict[str, Any]] = []
    for change_id, runs in grouped.items():
        ordered = sorted(runs, key=lambda item: (item.created_at, item.run_id))
        latest = ordered[-1]
        items.append(
            {
                "change_id": change_id,
                "run_count": len(ordered),
                "latest_run_id": latest.run_id,
                "latest_status": latest.status,
                "latest_created_at": latest.created_at.isoformat(),
                "failed_run_count": sum(item.status == "failed" for item in ordered),
            }
        )
    return tuple(sorted(items, key=lambda item: item["change_id"]))


def review_queue_view(
    repository: SQLiteWorkflowRepository,
) -> tuple[dict[str, Any], ...]:
    """Return durable review cases enriched with run/change context."""

    items: list[dict[str, Any]] = []
    for run in repository.list_runs():
        for review in repository.list_review_cases(run.run_id):
            items.append(
                {
                    **review,
                    "change_id": run.change_id,
                    "run_status": run.status,
                }
            )
    status_order = {"open": 0, "in_review": 1, "escalated": 2, "resolved": 3}
    return tuple(
        sorted(
            items,
            key=lambda item: (
                status_order.get(item["status"], 99),
                item["created_at"],
                item["review_id"],
            ),
        )
    )


def case_trace_view(
    repository: SQLiteWorkflowRepository,
    run_id: str,
) -> dict[str, Any]:
    """Build one compact operator-facing workflow trace."""

    run = repository.get_run(run_id)
    return {
        "run": {
            "run_id": run.run_id,
            "change_id": run.change_id,
            "status": run.status,
            "created_at": run.created_at.isoformat(),
            "request_sha256": run.request_sha256,
            "failed_step": run.failed_step,
            "error_code": run.error_code,
            "retryable": run.retryable,
            "error_detail": run.error_detail,
        },
        "result_summary": run.result_payload.get("summary", {}),
        "steps": list(repository.list_steps(run_id)),
        "reviews": list(repository.list_review_cases(run_id)),
        "audit_events": list(repository.list_audit_events(run_id)),
        "compliance_determination_produced": run.result_payload.get(
            "compliance_determination_produced", False
        ),
    }
