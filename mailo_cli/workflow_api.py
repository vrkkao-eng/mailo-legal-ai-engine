"""Pydantic transport schemas for the stateless RegAI workflow API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from mailo_cli.regulatory.controls import (
    Control,
    ControlImplementationStatus,
    ControlType,
    ObligationControlMapping,
)
from mailo_cli.regulatory.evidence import (
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceSet,
    EvidenceType,
)
from mailo_cli.regulatory.models import ChangeType, RegulatoryChange, SourceLocator
from mailo_cli.regulatory.obligations import Obligation, ObligationModality
from mailo_cli.regulatory.service import WorkflowEvaluationResult


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocatorPayload(StrictModel):
    provision: str = Field(min_length=1)
    paragraph: str | None = None
    point: str | None = None
    subparagraph: str | None = None

    def to_domain(self) -> SourceLocator:
        return SourceLocator(**self.model_dump())


class RegulatoryChangePayload(StrictModel):
    change_id: str = Field(min_length=1)
    change_type: ChangeType
    source_id: str = Field(min_length=1)
    old_version_id: str = Field(min_length=1)
    new_version_id: str = Field(min_length=1)
    effective_date: date
    amendment_source_id: str = Field(min_length=1)
    amendment_locator: LocatorPayload
    source_url: HttpUrl
    summary: str = Field(min_length=1)
    old_locator: LocatorPayload | None = None
    new_locator: LocatorPayload | None = None

    def to_domain(self) -> RegulatoryChange:
        return RegulatoryChange(
            change_id=self.change_id,
            change_type=self.change_type,
            source_id=self.source_id,
            old_version_id=self.old_version_id,
            new_version_id=self.new_version_id,
            effective_date=self.effective_date,
            amendment_source_id=self.amendment_source_id,
            amendment_locator=self.amendment_locator.to_domain(),
            source_url=str(self.source_url),
            summary=self.summary,
            old_locator=self.old_locator.to_domain() if self.old_locator else None,
            new_locator=self.new_locator.to_domain() if self.new_locator else None,
        )


class ObligationPayload(StrictModel):
    obligation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    locator: LocatorPayload
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    object: str = Field(min_length=1)
    modality: ObligationModality
    condition: str | None = None
    effective_condition: str | None = None
    source_url: HttpUrl | None = None
    mailo_concept: str | None = None

    def to_domain(self) -> Obligation:
        return Obligation(
            obligation_id=self.obligation_id,
            source_id=self.source_id,
            locator=self.locator.to_domain(),
            actor=self.actor,
            action=self.action,
            object=self.object,
            modality=self.modality,
            condition=self.condition,
            effective_condition=self.effective_condition,
            source_url=str(self.source_url) if self.source_url else None,
            mailo_concept=self.mailo_concept,
        )


class MappingPayload(StrictModel):
    obligation_id: str = Field(min_length=1)
    control_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed: bool = True

    def to_domain(self) -> ObligationControlMapping:
        return ObligationControlMapping(**self.model_dump())


class ControlPayload(StrictModel):
    control_id: str = Field(min_length=1)
    obligation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    control_type: ControlType
    owner_role: str = Field(min_length=1)
    implementation_status: ControlImplementationStatus = (
        ControlImplementationStatus.NOT_ASSESSED
    )
    source: str | None = None

    def to_domain(self) -> Control:
        return Control(**self.model_dump())


class EvidenceRequirementPayload(StrictModel):
    requirement_id: str = Field(min_length=1)
    control_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_type: EvidenceType
    mandatory: bool = True
    source: str = "reviewed control design"

    def to_domain(self) -> EvidenceRequirement:
        return EvidenceRequirement(**self.model_dump())


class EvidenceRecordPayload(StrictModel):
    evidence_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    evidence_type: EvidenceType
    source_uri: HttpUrl
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    collected_at: datetime
    owner_role: str = Field(min_length=1)

    def to_domain(self) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=self.evidence_id,
            requirement_id=self.requirement_id,
            title=self.title,
            evidence_type=self.evidence_type,
            source_uri=str(self.source_uri),
            sha256=self.sha256,
            collected_at=self.collected_at,
            owner_role=self.owner_role,
        )


class EvidenceSetPayload(StrictModel):
    requirements: list[EvidenceRequirementPayload] = Field(min_length=1)
    records: list[EvidenceRecordPayload] = Field(default_factory=list)

    def to_domain(self) -> EvidenceSet:
        return EvidenceSet(
            requirements=tuple(item.to_domain() for item in self.requirements),
            records=tuple(item.to_domain() for item in self.records),
        )


class WorkflowEvaluateRequest(StrictModel):
    change: RegulatoryChangePayload
    obligations: list[ObligationPayload] = Field(min_length=1)
    mappings: list[MappingPayload] = Field(default_factory=list)
    controls: list[ControlPayload] = Field(default_factory=list)
    evidence: EvidenceSetPayload


class WorkflowSummaryResponse(StrictModel):
    evidence_gap_count: int
    regulatory_impact_count: int
    route_count: int
    human_review_count: int
    log_only_count: int


class EvidenceGapResponse(StrictModel):
    requirement_id: str
    control_id: str
    status: str
    reason: str


class RegulatoryImpactResponse(StrictModel):
    change_id: str
    obligation_id: str
    control_id: str | None
    requirement_ids: list[str]
    upstream_link_status: str
    status: str
    reason: str


class ReviewQuestionResponse(StrictModel):
    question_id: str
    prompt: str
    permitted_answers: list[Literal["yes", "no", "unknown"]]
    context_refs: list[str]


class ReviewRouteResponse(StrictModel):
    subject_type: str
    subject_id: str
    disposition: str
    reason_code: str
    reviewer_role: str | None
    question: ReviewQuestionResponse | None


class WorkflowEvaluateResponse(StrictModel):
    summary: WorkflowSummaryResponse
    evidence_gaps: list[EvidenceGapResponse]
    regulatory_impacts: list[RegulatoryImpactResponse]
    review_routes: list[ReviewRouteResponse]
    compliance_determination_produced: bool

    @classmethod
    def from_domain(cls, result: WorkflowEvaluationResult) -> "WorkflowEvaluateResponse":
        return cls.model_validate(result.to_dict())


def to_domain_request(
    request: WorkflowEvaluateRequest,
) -> tuple[
    RegulatoryChange,
    tuple[Obligation, ...],
    tuple[ObligationControlMapping, ...],
    tuple[Control, ...],
    EvidenceSet,
]:
    return (
        request.change.to_domain(),
        tuple(item.to_domain() for item in request.obligations),
        tuple(item.to_domain() for item in request.mappings),
        tuple(item.to_domain() for item in request.controls),
        request.evidence.to_domain(),
    )



class EscalationResponse(StrictModel):
    escalation_id: str
    review_id: str
    target_role: str
    reason: str
    escalated_at: str


class PersistedReviewCaseResponse(StrictModel):
    review_id: str
    run_id: str
    subject_type: str
    subject_id: str
    reviewer_role: str
    status: str
    question: dict[str, object]
    created_at: str
    escalation: EscalationResponse | None = None


class AuditEventResponse(StrictModel):
    event_id: str
    review_id: str
    event_type: str
    actor_role: str
    occurred_at: str
    detail: str


class WorkflowRunResponse(StrictModel):
    run_id: str
    idempotency_key: str
    request_sha256: str
    change_id: str
    status: str
    created_at: str
    created: bool
    result: dict[str, object]
    review_cases: list[PersistedReviewCaseResponse]
    audit_events: list[AuditEventResponse]


class HumanResponsePersistRequest(StrictModel):
    response_id: str = Field(min_length=1, max_length=191)
    answer: Literal["yes", "no", "unknown"]
    reviewer_role: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    responded_at: datetime
    escalation_target: str | None = None


class HumanResponsePersistResponse(StrictModel):
    review_case: PersistedReviewCaseResponse
    audit_events: list[AuditEventResponse]
