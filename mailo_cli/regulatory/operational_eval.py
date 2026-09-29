"""Operational evaluation for persisted RegAI workflow execution."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from statistics import mean, median

from .persistence import PersistedWorkflowRun, SQLiteWorkflowRepository


@dataclass(frozen=True, slots=True)
class OperationalEvalReport:
    run_count: int
    completed_count: int
    failed_count: int
    running_count: int
    completion_rate: float
    retryable_failure_count: int
    non_retryable_failure_count: int
    failure_codes: dict[str, int]
    step_event_count: int
    mean_step_ms: float
    p50_step_ms: float
    p95_step_ms: float
    replay_group_count: int
    replay_consistent_group_count: int
    replay_consistency: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def _replay_signature(run: PersistedWorkflowRun) -> tuple[object, ...]:
    return (
        run.status,
        run.failed_step,
        run.error_code,
        run.retryable,
        run.result_payload,
    )


def evaluate_operations(
    repository: SQLiteWorkflowRepository,
) -> OperationalEvalReport:
    """Evaluate persisted execution behaviour without scoring legal quality."""

    runs = repository.list_runs()
    completed = tuple(run for run in runs if run.status == "completed")
    failed = tuple(run for run in runs if run.status == "failed")
    running = tuple(run for run in runs if run.status == "running")

    durations: list[float] = []
    for run in runs:
        durations.extend(
            float(step["duration_ms"]) for step in repository.list_steps(run.run_id)
        )

    failure_codes = Counter(
        run.error_code for run in failed if run.error_code is not None
    )

    by_request: dict[str, list[PersistedWorkflowRun]] = defaultdict(list)
    for run in runs:
        by_request[run.request_sha256].append(run)

    replay_groups = [group for group in by_request.values() if len(group) > 1]
    consistent = 0
    for group in replay_groups:
        signature = _replay_signature(group[0])
        if all(_replay_signature(item) == signature for item in group[1:]):
            consistent += 1

    return OperationalEvalReport(
        run_count=len(runs),
        completed_count=len(completed),
        failed_count=len(failed),
        running_count=len(running),
        completion_rate=_ratio(len(completed), len(runs)),
        retryable_failure_count=sum(run.retryable is True for run in failed),
        non_retryable_failure_count=sum(run.retryable is False for run in failed),
        failure_codes=dict(sorted(failure_codes.items())),
        step_event_count=len(durations),
        mean_step_ms=mean(durations) if durations else 0.0,
        p50_step_ms=median(durations) if durations else 0.0,
        p95_step_ms=_percentile(durations, 0.95),
        replay_group_count=len(replay_groups),
        replay_consistent_group_count=consistent,
        replay_consistency=_ratio(consistent, len(replay_groups)),
    )
