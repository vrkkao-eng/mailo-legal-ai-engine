"""Application-layer compliance controls mapped from reviewed obligations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ControlType(str, Enum):
    ASSESSMENT = "assessment"
    DOCUMENTATION = "documentation"
    GOVERNANCE = "governance"
    MONITORING = "monitoring"
    NOTIFICATION = "notification"
    TECHNICAL = "technical"


class ControlImplementationStatus(str, Enum):
    NOT_ASSESSED = "not_assessed"
    PLANNED = "planned"
    IMPLEMENTED = "implemented"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class Control:
    """Organisation-layer control linked to a reviewed legal obligation.

    A Control is operational workflow data. It does not amend MAILO's
    canonical legal semantics and its status is not a legal-compliance verdict.
    """

    control_id: str
    obligation_id: str
    title: str
    description: str
    control_type: ControlType
    owner_role: str
    implementation_status: ControlImplementationStatus = ControlImplementationStatus.NOT_ASSESSED
    source: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("control_id", "obligation_id", "title", "description", "owner_role"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        if self.source is not None:
            source = self.source.strip()
            if not source:
                raise ValueError("source must not be blank")
            object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class ObligationControlMapping:
    """Reviewed mapping between one obligation and one operational control."""

    obligation_id: str
    control_id: str
    rationale: str
    reviewed: bool = True

    def __post_init__(self) -> None:
        for field_name in ("obligation_id", "control_id", "rationale"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        if not self.reviewed:
            raise ValueError("v0.4.0 mappings must be reviewed")
