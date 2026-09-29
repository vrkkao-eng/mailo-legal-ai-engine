"""Operational step events and failure semantics for durable workflow runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class WorkflowStep(str, Enum):
    EVALUATE = "evaluate"
    PERSIST = "persist"
    REVIEW_READY = "review_ready"


class WorkflowStepStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowErrorCode(str, Enum):
    DOMAIN_VALIDATION_FAILED = "domain_validation_failed"
    PERSISTENCE_FAILED = "persistence_failed"
    REVIEW_PERSISTENCE_FAILED = "review_persistence_failed"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True, slots=True)
class WorkflowStepEvent:
    step: WorkflowStep
    status: WorkflowStepStatus
    duration_ms: float
    detail: str
    error_code: WorkflowErrorCode | None = None
    retryable: bool | None = None

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["step"] = self.step.value
        result["status"] = self.status.value
        result["error_code"] = self.error_code.value if self.error_code else None
        return result
