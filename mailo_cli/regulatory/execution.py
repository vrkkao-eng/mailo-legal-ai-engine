"""Observable orchestration for durable RegAI workflow execution."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable

from .controls import Control, ObligationControlMapping
from .evidence import EvidenceRecord, EvidenceSet
from .models import RegulatoryChange
from .obligations import Obligation
from .observability import (
    WorkflowErrorCode,
    WorkflowStep,
    WorkflowStepEvent,
    WorkflowStepStatus,
)
from .persistence import PersistedWorkflowRun, SQLiteWorkflowRepository
from .service import evaluate_workflow


@dataclass(frozen=True, slots=True)
class WorkflowExecutionError(Exception):
    run_id: str
    failed_step: WorkflowStep
    error_code: WorkflowErrorCode
    retryable: bool
    detail: str

    def __str__(self) -> str:
        return self.detail


def execute_durable_workflow(
    *,
    repository: SQLiteWorkflowRepository,
    idempotency_key: str,
    request_payload: dict[str, Any],
    change: RegulatoryChange,
    obligations: Iterable[Obligation],
    mappings: Iterable[ObligationControlMapping],
    controls: Iterable[Control],
    evidence: EvidenceSet,
) -> tuple[PersistedWorkflowRun, bool]:
    """Reserve, evaluate and persist one observable durable workflow run."""

    run, created = repository.reserve_run(
        idempotency_key=idempotency_key,
        request_payload=request_payload,
        change_id=change.change_id,
    )
    if not created:
        return run, False

    started = time.perf_counter()
    try:
        result = evaluate_workflow(
            change,
            obligations=tuple(obligations),
            mappings=tuple(mappings),
            controls=tuple(controls),
            evidence=evidence,
        )
    except (ValueError, TypeError) as exc:
        duration = round((time.perf_counter() - started) * 1000, 3)
        event = WorkflowStepEvent(
            step=WorkflowStep.EVALUATE,
            status=WorkflowStepStatus.FAILED,
            duration_ms=duration,
            detail=str(exc),
            error_code=WorkflowErrorCode.DOMAIN_VALIDATION_FAILED,
            retryable=False,
        )
        repository.append_step(run.run_id, event)
        repository.mark_failed(
            run.run_id,
            failed_step=WorkflowStep.EVALUATE.value,
            error_code=WorkflowErrorCode.DOMAIN_VALIDATION_FAILED,
            retryable=False,
            detail=str(exc),
        )
        raise WorkflowExecutionError(
            run_id=run.run_id,
            failed_step=WorkflowStep.EVALUATE,
            error_code=WorkflowErrorCode.DOMAIN_VALIDATION_FAILED,
            retryable=False,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        duration = round((time.perf_counter() - started) * 1000, 3)
        repository.append_step(
            run.run_id,
            WorkflowStepEvent(
                step=WorkflowStep.EVALUATE,
                status=WorkflowStepStatus.FAILED,
                duration_ms=duration,
                detail="Unexpected evaluation failure.",
                error_code=WorkflowErrorCode.INTERNAL_ERROR,
                retryable=False,
            ),
        )
        repository.mark_failed(
            run.run_id,
            failed_step=WorkflowStep.EVALUATE.value,
            error_code=WorkflowErrorCode.INTERNAL_ERROR,
            retryable=False,
            detail="Unexpected evaluation failure.",
        )
        raise WorkflowExecutionError(
            run_id=run.run_id,
            failed_step=WorkflowStep.EVALUATE,
            error_code=WorkflowErrorCode.INTERNAL_ERROR,
            retryable=False,
            detail="Unexpected evaluation failure.",
        ) from exc

    repository.append_step(
        run.run_id,
        WorkflowStepEvent(
            step=WorkflowStep.EVALUATE,
            status=WorkflowStepStatus.SUCCESS,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            detail="Workflow candidates and review routes evaluated.",
        ),
    )

    started = time.perf_counter()
    try:
        completed = repository.finalize_run(
            run.run_id,
            result=result,
            evidence_records=evidence.records,
        )
    except Exception as exc:
        duration = round((time.perf_counter() - started) * 1000, 3)
        try:
            repository.append_step(
                run.run_id,
                WorkflowStepEvent(
                    step=WorkflowStep.PERSIST,
                    status=WorkflowStepStatus.FAILED,
                    duration_ms=duration,
                    detail="Transactional workflow persistence failed.",
                    error_code=WorkflowErrorCode.PERSISTENCE_FAILED,
                    retryable=True,
                ),
            )
            repository.mark_failed(
                run.run_id,
                failed_step=WorkflowStep.PERSIST.value,
                error_code=WorkflowErrorCode.PERSISTENCE_FAILED,
                retryable=True,
                detail="Transactional workflow persistence failed.",
            )
        except Exception:
            pass
        raise WorkflowExecutionError(
            run_id=run.run_id,
            failed_step=WorkflowStep.PERSIST,
            error_code=WorkflowErrorCode.PERSISTENCE_FAILED,
            retryable=True,
            detail="Transactional workflow persistence failed.",
        ) from exc

    repository.append_step(
        run.run_id,
        WorkflowStepEvent(
            step=WorkflowStep.PERSIST,
            status=WorkflowStepStatus.SUCCESS,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            detail="Workflow result, evidence metadata, reviews and audit events committed.",
        ),
    )
    repository.append_step(
        run.run_id,
        WorkflowStepEvent(
            step=WorkflowStep.REVIEW_READY,
            status=WorkflowStepStatus.SUCCESS,
            duration_ms=0.0,
            detail=f"{len(repository.list_review_cases(run.run_id))} review cases ready.",
        ),
    )
    return completed, True
