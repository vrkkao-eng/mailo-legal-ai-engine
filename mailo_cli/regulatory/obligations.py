"""Application-layer obligation representations for RegAI applicability work."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import SourceLocator


class ObligationModality(str, Enum):
    MUST = "must"
    MUST_NOT = "must_not"
    MAY = "may"


@dataclass(frozen=True, slots=True)
class Obligation:
    """Reviewed obligation unit linked to a legal source.

    This is application-layer workflow data, not a replacement for canonical
    MAILO ontology concepts and not a compliance determination.
    """

    obligation_id: str
    source_id: str
    locator: SourceLocator
    actor: str
    action: str
    object: str
    modality: ObligationModality
    condition: str | None = None
    effective_condition: str | None = None
    source_url: str | None = None
    mailo_concept: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("obligation_id", "source_id", "actor", "action", "object"):
            value = getattr(self, field_name).strip()
            if not value:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, value)
        for field_name in ("condition", "effective_condition", "source_url", "mailo_concept"):
            value = getattr(self, field_name)
            if value is not None:
                value = value.strip()
                if not value:
                    raise ValueError(f"{field_name} must not be blank")
                object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True)
class SystemDescription:
    """Minimal factual description supplied for later applicability analysis."""

    system_id: str
    actor_roles: tuple[str, ...]
    system_kind: str
    facts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.system_id.strip():
            raise ValueError("system_id must not be empty")
        if not self.system_kind.strip():
            raise ValueError("system_kind must not be empty")
        if not self.actor_roles:
            raise ValueError("actor_roles must not be empty")
        if any(not role.strip() for role in self.actor_roles):
            raise ValueError("actor_roles must not contain blank values")


class ApplicabilityStatus(str, Enum):
    APPLIES = "applies"
    DOES_NOT_APPLY = "does_not_apply"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class ApplicabilityAssessment:
    obligation_id: str
    system_id: str
    status: ApplicabilityStatus
    reasons: tuple[str, ...]
    missing_facts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("applicability assessment requires at least one reason")
        if self.status is ApplicabilityStatus.REVIEW_REQUIRED and not self.missing_facts:
            raise ValueError("review_required assessments must identify missing facts")
