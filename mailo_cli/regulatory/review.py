"""Focused human-review routing and append-only audit contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .impact import ImpactLinkStatus
from .workflow_impact import (
    EvidenceGapCandidate,
    EvidenceGapStatus,
    RegulatoryImpactCandidate,
)


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _identifier(value: str, field_name: str) -> str:
    value = value.strip()
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} must be a stable identifier")
    return value


def _text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value


class ReviewSubjectType(str, Enum):
    EVIDENCE_GAP = "evidence_gap"
    REGULATORY_IMPACT = "regulatory_impact"


class ReviewDisposition(str, Enum):
    HUMAN_REVIEW = "human_review"
    LOG_ONLY = "log_only"


class ReviewReasonCode(str, Enum):
    MISSING_REGISTERED_EVIDENCE = "missing_registered_evidence"
    OPTIONAL_EVIDENCE_NOT_REGISTERED = "optional_evidence_not_registered"
    REGULATORY_CHANGE_EXACT_LINK = "regulatory_change_exact_link"
    REGULATORY_CHANGE_INTERPRETIVE_LINK = "regulatory_change_interpretive_link"


class ReviewAnswer(str, Enum):
    """Permitted micro-review answers.

    There is intentionally no approve/reject/compliant/non-compliant answer.
    """

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ReviewStatus(str, Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class AuditEventType(str, Enum):
    REVIEW_CREATED = "review_created"
    REVIEW_STARTED = "review_started"
    RESPONSE_RECORDED = "response_recorded"
    INFORMATION_REQUESTED = "information_requested"
    ESCALATED = "escalated"
    REVIEW_CLOSED = "review_closed"


@dataclass(frozen=True, slots=True)
class ReviewQuestion:
    """One focused factual or interpretive question for a human reviewer."""

    question_id: str
    prompt: str
    permitted_answers: tuple[ReviewAnswer, ...]
    context_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_id", _identifier(self.question_id, "question_id"))
        object.__setattr__(self, "prompt", _text(self.prompt, "prompt"))
        if not self.permitted_answers:
            raise ValueError("permitted_answers must not be empty")
        if any(not isinstance(answer, ReviewAnswer) for answer in self.permitted_answers):
            raise TypeError("permitted_answers must contain ReviewAnswer values")
        if len(self.permitted_answers) != len(set(self.permitted_answers)):
            raise ValueError("permitted_answers must not contain duplicates")
        refs = tuple(_identifier(value, "context_ref") for value in self.context_refs)
        object.__setattr__(self, "context_refs", refs)


@dataclass(frozen=True, slots=True)
class ReviewRoute:
    """Routing result for a machine-generated workflow candidate."""

    subject_type: ReviewSubjectType
    subject_id: str
    disposition: ReviewDisposition
    reason_code: ReviewReasonCode
    reviewer_role: str | None = None
    question: ReviewQuestion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.subject_type, ReviewSubjectType):
            raise TypeError("subject_type must be a ReviewSubjectType")
        if not isinstance(self.disposition, ReviewDisposition):
            raise TypeError("disposition must be a ReviewDisposition")
        if not isinstance(self.reason_code, ReviewReasonCode):
            raise TypeError("reason_code must be a ReviewReasonCode")
        object.__setattr__(self, "subject_id", _identifier(self.subject_id, "subject_id"))

        if self.disposition is ReviewDisposition.HUMAN_REVIEW:
            if self.reviewer_role is None or self.question is None:
                raise ValueError("human review requires reviewer_role and question")
            object.__setattr__(
                self, "reviewer_role", _text(self.reviewer_role, "reviewer_role")
            )
        else:
            if self.reviewer_role is not None or self.question is not None:
                raise ValueError("log-only routes must not create a reviewer task")


def route_review_candidate(
    candidate: EvidenceGapCandidate | RegulatoryImpactCandidate,
) -> ReviewRoute:
    """Route a candidate without exposing or inventing a compliance verdict."""

    answers = (ReviewAnswer.YES, ReviewAnswer.NO, ReviewAnswer.UNKNOWN)

    if isinstance(candidate, EvidenceGapCandidate):
        if candidate.status is EvidenceGapStatus.OPTIONAL_NO_RECORD:
            return ReviewRoute(
                subject_type=ReviewSubjectType.EVIDENCE_GAP,
                subject_id=candidate.requirement_id,
                disposition=ReviewDisposition.LOG_ONLY,
                reason_code=ReviewReasonCode.OPTIONAL_EVIDENCE_NOT_REGISTERED,
            )

        return ReviewRoute(
            subject_type=ReviewSubjectType.EVIDENCE_GAP,
            subject_id=candidate.requirement_id,
            disposition=ReviewDisposition.HUMAN_REVIEW,
            reason_code=ReviewReasonCode.MISSING_REGISTERED_EVIDENCE,
            reviewer_role="AI governance",
            question=ReviewQuestion(
                question_id=f"q:{candidate.requirement_id}:external-evidence",
                prompt=(
                    "Could the required artefact exist outside the currently "
                    "indexed evidence source?"
                ),
                permitted_answers=answers,
                context_refs=(candidate.requirement_id, candidate.control_id),
            ),
        )

    if isinstance(candidate, RegulatoryImpactCandidate):
        control_ref = candidate.control_id or candidate.obligation_id
        exact = candidate.upstream_link_status is ImpactLinkStatus.LOCATOR_MATCH
        if candidate.control_id is None:
            prompt = (
                "Does this regulatory change require a reviewed control mapping "
                "to be created or updated for the affected obligation?"
            )
        else:
            prompt = (
                "Does the reviewed regulatory change alter the basis or scope of "
                "this existing control mapping?"
            )

        return ReviewRoute(
            subject_type=ReviewSubjectType.REGULATORY_IMPACT,
            subject_id=f"{candidate.change_id}:{control_ref}",
            disposition=ReviewDisposition.HUMAN_REVIEW,
            reason_code=(
                ReviewReasonCode.REGULATORY_CHANGE_EXACT_LINK
                if exact
                else ReviewReasonCode.REGULATORY_CHANGE_INTERPRETIVE_LINK
            ),
            reviewer_role="Legal",
            question=ReviewQuestion(
                question_id=f"q:{candidate.change_id}:{control_ref}",
                prompt=prompt,
                permitted_answers=answers,
                context_refs=tuple(
                    value
                    for value in (
                        candidate.change_id,
                        candidate.obligation_id,
                        candidate.control_id,
                        *candidate.requirement_ids,
                    )
                    if value is not None
                ),
            ),
        )

    raise TypeError("unsupported review candidate type")


@dataclass(frozen=True, slots=True)
class ReviewCase:
    """Human-review work item created only from a HUMAN_REVIEW route."""

    review_id: str
    route: ReviewRoute
    status: ReviewStatus
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "review_id", _identifier(self.review_id, "review_id"))
        if self.route.disposition is not ReviewDisposition.HUMAN_REVIEW:
            raise ValueError("ReviewCase requires a HUMAN_REVIEW route")
        if not isinstance(self.status, ReviewStatus):
            raise TypeError("status must be a ReviewStatus")
        _aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class HumanResponse:
    """Human answer to the focused review question."""

    response_id: str
    review_id: str
    answer: ReviewAnswer
    reviewer_role: str
    rationale: str
    responded_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "response_id", _identifier(self.response_id, "response_id")
        )
        object.__setattr__(self, "review_id", _identifier(self.review_id, "review_id"))
        if not isinstance(self.answer, ReviewAnswer):
            raise TypeError("answer must be a ReviewAnswer")
        object.__setattr__(
            self, "reviewer_role", _text(self.reviewer_role, "reviewer_role")
        )
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        _aware(self.responded_at, "responded_at")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Append-only audit event for one review case."""

    event_id: str
    review_id: str
    event_type: AuditEventType
    actor_role: str
    occurred_at: datetime
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _identifier(self.event_id, "event_id"))
        object.__setattr__(self, "review_id", _identifier(self.review_id, "review_id"))
        if not isinstance(self.event_type, AuditEventType):
            raise TypeError("event_type must be an AuditEventType")
        object.__setattr__(self, "actor_role", _text(self.actor_role, "actor_role"))
        object.__setattr__(self, "detail", _text(self.detail, "detail"))
        _aware(self.occurred_at, "occurred_at")


@dataclass(frozen=True, slots=True)
class Escalation:
    """Explicit routing of an unresolved review to another competent role."""

    escalation_id: str
    review_id: str
    target_role: str
    reason: str
    escalated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "escalation_id", _identifier(self.escalation_id, "escalation_id")
        )
        object.__setattr__(self, "review_id", _identifier(self.review_id, "review_id"))
        object.__setattr__(self, "target_role", _text(self.target_role, "target_role"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        _aware(self.escalated_at, "escalated_at")


@dataclass(frozen=True, slots=True)
class ReviewTrail:
    """Validated snapshot of a focused human-review history.

    The trail checks workflow integrity only. RESOLVED means the review case was
    handled; it does not mean a legal or compliance issue was resolved.
    """

    case: ReviewCase
    responses: tuple[HumanResponse, ...]
    audit_events: tuple[AuditEvent, ...]
    escalation: Escalation | None = None

    def __post_init__(self) -> None:
        review_id = self.case.review_id

        response_ids = [item.response_id for item in self.responses]
        if len(response_ids) != len(set(response_ids)):
            raise ValueError("duplicate response_id values are not allowed")

        event_ids = [item.event_id for item in self.audit_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate event_id values are not allowed")

        for response in self.responses:
            if response.review_id != review_id:
                raise ValueError("response references a different review")
            if response.responded_at < self.case.created_at:
                raise ValueError("response predates review creation")
            if response.answer not in self.case.route.question.permitted_answers:
                raise ValueError("response answer is not permitted by the review question")

        for event in self.audit_events:
            if event.review_id != review_id:
                raise ValueError("audit event references a different review")
            if event.occurred_at < self.case.created_at:
                raise ValueError("audit event predates review creation")

        event_times = [event.occurred_at for event in self.audit_events]
        if event_times != sorted(event_times):
            raise ValueError("audit events must be append-only chronological")

        if not self.audit_events:
            raise ValueError("review trail requires audit events")
        if self.audit_events[0].event_type is not AuditEventType.REVIEW_CREATED:
            raise ValueError("first audit event must be REVIEW_CREATED")
        if sum(
            event.event_type is AuditEventType.REVIEW_CREATED
            for event in self.audit_events
        ) != 1:
            raise ValueError("review trail requires exactly one REVIEW_CREATED event")

        if self.escalation is not None:
            if self.escalation.review_id != review_id:
                raise ValueError("escalation references a different review")
            if self.escalation.escalated_at < self.case.created_at:
                raise ValueError("escalation predates review creation")

        if self.case.status is ReviewStatus.OPEN:
            if self.responses:
                raise ValueError("open review must not already contain a response")
            if self.escalation is not None:
                raise ValueError("open review must not contain an escalation")

        if self.case.status is ReviewStatus.IN_REVIEW and not any(
            event.event_type is AuditEventType.REVIEW_STARTED
            for event in self.audit_events
        ):
            raise ValueError("in-review case requires REVIEW_STARTED audit event")

        if self.case.status is ReviewStatus.RESOLVED:
            if not self.responses:
                raise ValueError("resolved review requires a human response")
            if self.responses[-1].answer is ReviewAnswer.UNKNOWN:
                raise ValueError("UNKNOWN response cannot resolve a review")
            if self.escalation is not None:
                raise ValueError("resolved review must not retain an escalation")
            if not any(
                event.event_type is AuditEventType.REVIEW_CLOSED
                for event in self.audit_events
            ):
                raise ValueError("resolved review requires REVIEW_CLOSED audit event")

        if self.case.status is ReviewStatus.ESCALATED:
            if self.escalation is None:
                raise ValueError("escalated review requires escalation details")
            if not any(
                event.event_type is AuditEventType.ESCALATED
                for event in self.audit_events
            ):
                raise ValueError("escalated review requires ESCALATED audit event")


def create_review_trail(
    route: ReviewRoute,
    review_id: str,
    created_at: datetime,
) -> ReviewTrail:
    """Create an OPEN review with its first append-only audit event."""

    case = ReviewCase(
        review_id=review_id,
        route=route,
        status=ReviewStatus.OPEN,
        created_at=created_at,
    )
    event = AuditEvent(
        event_id=f"evt:{review_id}:created",
        review_id=review_id,
        event_type=AuditEventType.REVIEW_CREATED,
        actor_role="system",
        occurred_at=created_at,
        detail="Focused human review created from a routed workflow candidate.",
    )
    return ReviewTrail(case=case, responses=(), audit_events=(event,))
