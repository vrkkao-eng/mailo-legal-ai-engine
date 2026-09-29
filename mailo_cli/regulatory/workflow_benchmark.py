"""Deterministic evaluation for the v0.4.x end-to-end RegAI workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .review import (
    AuditEventType,
    ReviewAnswer,
    ReviewDisposition,
    ReviewRoute,
    ReviewStatus,
    ReviewTrail,
)


@dataclass(frozen=True, slots=True)
class WorkflowRouteGold:
    """Expected routing outcome for one fixed workflow candidate."""

    subject_id: str
    expected_disposition: ReviewDisposition
    expected_reviewer_role: str | None = None
    expected_context_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowGold:
    """Reviewed expectations for a fixed workflow scenario."""

    routes: tuple[WorkflowRouteGold, ...]
    expected_audit_subject_ids: tuple[str, ...] = ()
    expected_escalation_subject_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowBenchmarkReport:
    """Engineering evaluation report; burden fields are proxies, not human measures."""

    route_count: int
    expected_route_count: int
    routing_correct: int
    routing_accuracy: float
    traceable_route_count: int
    traceability_completeness: float
    human_review_count: int
    log_only_count: int
    human_review_share: float
    audit_case_count: int
    expected_audit_case_count: int
    audit_complete_count: int
    audit_trace_completeness: float
    escalation_case_count: int
    escalation_integrity_count: int
    escalation_integrity_rate: float
    unsafe_unknown_resolutions: int
    burden_proxy_mean_context_refs: float
    burden_proxy_mean_question_chars: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def benchmark_workflow(
    routes: Iterable[ReviewRoute],
    trails: Iterable[ReviewTrail],
    gold: WorkflowGold,
) -> WorkflowBenchmarkReport:
    """Evaluate routing, traceability and audit integrity on a fixed gold set.

    The function does not evaluate legal correctness, reviewer competence, or
    cognitive load. Question/context statistics are workflow-burden proxies only.
    """

    route_list = tuple(routes)
    trail_list = tuple(trails)

    actual_by_subject: dict[str, ReviewRoute] = {}
    for route in route_list:
        if route.subject_id in actual_by_subject:
            raise ValueError(f"duplicate route subject_id: {route.subject_id}")
        actual_by_subject[route.subject_id] = route

    gold_by_subject: dict[str, WorkflowRouteGold] = {}
    for item in gold.routes:
        if item.subject_id in gold_by_subject:
            raise ValueError(f"duplicate gold subject_id: {item.subject_id}")
        gold_by_subject[item.subject_id] = item

    routing_correct = 0
    traceable = 0
    for subject_id, expected in gold_by_subject.items():
        actual = actual_by_subject.get(subject_id)
        if actual is None:
            continue
        role_correct = (
            actual.reviewer_role == expected.expected_reviewer_role
            if expected.expected_disposition is ReviewDisposition.HUMAN_REVIEW
            else actual.reviewer_role is None
        )
        if (
            actual.disposition is expected.expected_disposition
            and role_correct
        ):
            routing_correct += 1

        if expected.expected_disposition is ReviewDisposition.LOG_ONLY:
            if actual.question is None:
                traceable += 1
            continue

        if actual.question is None:
            continue
        if set(expected.expected_context_refs).issubset(set(actual.question.context_refs)):
            traceable += 1

    human_routes = tuple(
        route
        for route in route_list
        if route.disposition is ReviewDisposition.HUMAN_REVIEW
    )
    log_only_count = sum(
        route.disposition is ReviewDisposition.LOG_ONLY for route in route_list
    )

    trail_by_subject: dict[str, ReviewTrail] = {}
    for trail in trail_list:
        subject_id = trail.case.route.subject_id
        if subject_id in trail_by_subject:
            raise ValueError(f"duplicate audit trail subject_id: {subject_id}")
        trail_by_subject[subject_id] = trail

    expected_audit = set(gold.expected_audit_subject_ids)
    audit_complete = 0
    for subject_id in expected_audit:
        audit_trail = trail_by_subject.get(subject_id)
        if audit_trail is None:
            continue
        has_created = bool(audit_trail.audit_events) and (
            audit_trail.audit_events[0].event_type is AuditEventType.REVIEW_CREATED
        )
        has_terminal_event = (
            audit_trail.case.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW)
            or (
                audit_trail.case.status is ReviewStatus.RESOLVED
                and any(
                    event.event_type is AuditEventType.REVIEW_CLOSED
                    for event in audit_trail.audit_events
                )
            )
            or (
                audit_trail.case.status is ReviewStatus.ESCALATED
                and any(
                    event.event_type is AuditEventType.ESCALATED
                    for event in audit_trail.audit_events
                )
            )
        )
        if has_created and has_terminal_event:
            audit_complete += 1

    expected_escalations = set(gold.expected_escalation_subject_ids)
    escalation_integrity = 0
    for subject_id in expected_escalations:
        escalation_trail = trail_by_subject.get(subject_id)
        if (
            escalation_trail is not None
            and escalation_trail.case.status is ReviewStatus.ESCALATED
            and escalation_trail.escalation is not None
            and any(
                event.event_type is AuditEventType.ESCALATED
                for event in escalation_trail.audit_events
            )
        ):
            escalation_integrity += 1

    unsafe_unknown = 0
    for trail in trail_list:
        if (
            trail.case.status is ReviewStatus.RESOLVED
            and trail.responses
            and trail.responses[-1].answer is ReviewAnswer.UNKNOWN
        ):
            unsafe_unknown += 1

    context_counts = [
        len(route.question.context_refs)
        for route in human_routes
        if route.question is not None
    ]
    question_lengths = [
        len(route.question.prompt)
        for route in human_routes
        if route.question is not None
    ]

    return WorkflowBenchmarkReport(
        route_count=len(route_list),
        expected_route_count=len(gold.routes),
        routing_correct=routing_correct,
        routing_accuracy=_ratio(routing_correct, len(gold.routes)),
        traceable_route_count=traceable,
        traceability_completeness=_ratio(traceable, len(gold.routes)),
        human_review_count=len(human_routes),
        log_only_count=log_only_count,
        human_review_share=_ratio(len(human_routes), len(route_list)),
        audit_case_count=len(trail_list),
        expected_audit_case_count=len(expected_audit),
        audit_complete_count=audit_complete,
        audit_trace_completeness=_ratio(audit_complete, len(expected_audit)),
        escalation_case_count=len(expected_escalations),
        escalation_integrity_count=escalation_integrity,
        escalation_integrity_rate=_ratio(
            escalation_integrity, len(expected_escalations)
        ),
        unsafe_unknown_resolutions=unsafe_unknown,
        burden_proxy_mean_context_refs=_ratio(
            sum(context_counts), len(context_counts)
        ),
        burden_proxy_mean_question_chars=_ratio(
            sum(question_lengths), len(question_lengths)
        ),
    )
