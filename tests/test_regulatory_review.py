from datetime import datetime, timezone

import pytest

from mailo_cli.regulatory.impact import ImpactLinkStatus
from mailo_cli.regulatory.review import (
    AuditEvent,
    AuditEventType,
    Escalation,
    HumanResponse,
    ReviewAnswer,
    ReviewCase,
    ReviewDisposition,
    ReviewReasonCode,
    ReviewRoute,
    ReviewStatus,
    ReviewSubjectType,
    ReviewTrail,
    create_review_trail,
    route_review_candidate,
)
from mailo_cli.regulatory.workflow_impact import (
    EvidenceGapCandidate,
    EvidenceGapStatus,
    RegulatoryImpactCandidate,
    RegulatoryImpactStatus,
)


NOW = datetime(2026, 9, 29, 20, 30, tzinfo=timezone.utc)


def test_optional_gap_is_log_only_to_reduce_review_burden():
    candidate = EvidenceGapCandidate(
        requirement_id="req-optional",
        control_id="ctrl-1",
        status=EvidenceGapStatus.OPTIONAL_NO_RECORD,
        reason="No registered optional record.",
    )

    route = route_review_candidate(candidate)

    assert route.disposition is ReviewDisposition.LOG_ONLY
    assert route.question is None
    assert route.reviewer_role is None
    assert route.reason_code is ReviewReasonCode.OPTIONAL_EVIDENCE_NOT_REGISTERED


def test_mandatory_gap_routes_to_focused_question_with_unknown():
    candidate = EvidenceGapCandidate(
        requirement_id="req-mandatory",
        control_id="ctrl-1",
        status=EvidenceGapStatus.MANDATORY_NO_RECORD,
        reason="No registered mandatory record.",
    )

    route = route_review_candidate(candidate)

    assert route.disposition is ReviewDisposition.HUMAN_REVIEW
    assert route.reviewer_role == "AI governance"
    assert route.question is not None
    assert ReviewAnswer.UNKNOWN in route.question.permitted_answers
    assert "outside the currently indexed evidence source" in route.question.prompt


def test_regulatory_impact_routes_to_legal_without_ai_verdict():
    candidate = RegulatoryImpactCandidate(
        change_id="change-1",
        obligation_id="obl-1",
        control_id="ctrl-1",
        requirement_ids=("req-1", "req-2"),
        upstream_link_status=ImpactLinkStatus.REVIEW_REQUIRED,
        status=RegulatoryImpactStatus.REVIEW_REQUIRED,
        reason="Upstream legal change requires review.",
    )

    route = route_review_candidate(candidate)

    assert route.reviewer_role == "Legal"
    assert route.reason_code is ReviewReasonCode.REGULATORY_CHANGE_INTERPRETIVE_LINK
    assert route.question is not None
    assert set(route.question.permitted_answers) == {
        ReviewAnswer.YES,
        ReviewAnswer.NO,
        ReviewAnswer.UNKNOWN,
    }


def test_log_only_route_cannot_create_review_case():
    route = ReviewRoute(
        subject_type=ReviewSubjectType.EVIDENCE_GAP,
        subject_id="req-1",
        disposition=ReviewDisposition.LOG_ONLY,
        reason_code=ReviewReasonCode.OPTIONAL_EVIDENCE_NOT_REGISTERED,
    )

    with pytest.raises(ValueError, match="HUMAN_REVIEW"):
        ReviewCase(
            review_id="review-1",
            route=route,
            status=ReviewStatus.OPEN,
            created_at=NOW,
        )


def test_create_review_trail_starts_with_created_event():
    candidate = EvidenceGapCandidate(
        requirement_id="req-1",
        control_id="ctrl-1",
        status=EvidenceGapStatus.MANDATORY_NO_RECORD,
        reason="No record.",
    )
    route = route_review_candidate(candidate)

    trail = create_review_trail(route, "review-1", NOW)

    assert trail.case.status is ReviewStatus.OPEN
    assert trail.audit_events[0].event_type is AuditEventType.REVIEW_CREATED
    assert trail.responses == ()


def test_unknown_response_cannot_resolve_review():
    candidate = EvidenceGapCandidate(
        requirement_id="req-1",
        control_id="ctrl-1",
        status=EvidenceGapStatus.MANDATORY_NO_RECORD,
        reason="No record.",
    )
    route = route_review_candidate(candidate)
    case = ReviewCase("review-1", route, ReviewStatus.RESOLVED, NOW)
    response = HumanResponse(
        response_id="resp-1",
        review_id="review-1",
        answer=ReviewAnswer.UNKNOWN,
        reviewer_role="AI governance",
        rationale="The artefact location cannot be determined from current systems.",
        responded_at=NOW,
    )
    events = (
        AuditEvent(
            "evt-1",
            "review-1",
            AuditEventType.REVIEW_CREATED,
            "system",
            NOW,
            "created",
        ),
        AuditEvent(
            "evt-2",
            "review-1",
            AuditEventType.REVIEW_CLOSED,
            "AI governance",
            NOW,
            "closed",
        ),
    )

    with pytest.raises(ValueError, match="UNKNOWN"):
        ReviewTrail(case, (response,), events)


def test_resolved_review_requires_human_response_and_closed_event():
    candidate = EvidenceGapCandidate(
        requirement_id="req-1",
        control_id="ctrl-1",
        status=EvidenceGapStatus.MANDATORY_NO_RECORD,
        reason="No record.",
    )
    route = route_review_candidate(candidate)
    case = ReviewCase("review-1", route, ReviewStatus.RESOLVED, NOW)
    response = HumanResponse(
        response_id="resp-1",
        review_id="review-1",
        answer=ReviewAnswer.NO,
        reviewer_role="AI governance",
        rationale="The artefact does not exist outside the indexed source.",
        responded_at=NOW,
    )
    events = (
        AuditEvent(
            "evt-1",
            "review-1",
            AuditEventType.REVIEW_CREATED,
            "system",
            NOW,
            "created",
        ),
        AuditEvent(
            "evt-2",
            "review-1",
            AuditEventType.RESPONSE_RECORDED,
            "AI governance",
            NOW,
            "response recorded",
        ),
        AuditEvent(
            "evt-3",
            "review-1",
            AuditEventType.REVIEW_CLOSED,
            "AI governance",
            NOW,
            "review case closed",
        ),
    )

    trail = ReviewTrail(case, (response,), events)

    assert trail.case.status is ReviewStatus.RESOLVED


def test_escalated_review_requires_target_and_audit_event():
    candidate = RegulatoryImpactCandidate(
        change_id="change-1",
        obligation_id="obl-1",
        control_id="ctrl-1",
        requirement_ids=(),
        upstream_link_status=ImpactLinkStatus.REVIEW_REQUIRED,
        status=RegulatoryImpactStatus.REVIEW_REQUIRED,
        reason="Interpretive review required.",
    )
    route = route_review_candidate(candidate)
    case = ReviewCase("review-2", route, ReviewStatus.ESCALATED, NOW)
    response = HumanResponse(
        response_id="resp-2",
        review_id="review-2",
        answer=ReviewAnswer.UNKNOWN,
        reviewer_role="Legal",
        rationale="The legal effect cannot be determined from the available material.",
        responded_at=NOW,
    )
    escalation = Escalation(
        escalation_id="esc-1",
        review_id="review-2",
        target_role="Senior Legal",
        reason="Interpretation remains unresolved.",
        escalated_at=NOW,
    )
    events = (
        AuditEvent(
            "evt-1",
            "review-2",
            AuditEventType.REVIEW_CREATED,
            "system",
            NOW,
            "created",
        ),
        AuditEvent(
            "evt-2",
            "review-2",
            AuditEventType.RESPONSE_RECORDED,
            "Legal",
            NOW,
            "unknown response recorded",
        ),
        AuditEvent(
            "evt-3",
            "review-2",
            AuditEventType.ESCALATED,
            "Legal",
            NOW,
            "escalated",
        ),
    )

    trail = ReviewTrail(case, (response,), events, escalation)

    assert trail.case.status is ReviewStatus.ESCALATED
    assert trail.escalation.target_role == "Senior Legal"


def test_audit_events_must_be_chronological():
    candidate = EvidenceGapCandidate(
        requirement_id="req-1",
        control_id="ctrl-1",
        status=EvidenceGapStatus.MANDATORY_NO_RECORD,
        reason="No record.",
    )
    route = route_review_candidate(candidate)
    case = ReviewCase("review-1", route, ReviewStatus.IN_REVIEW, NOW)
    later = datetime(2026, 9, 29, 21, 0, tzinfo=timezone.utc)
    earlier = datetime(2026, 9, 29, 20, 45, tzinfo=timezone.utc)
    events = (
        AuditEvent(
            "evt-1",
            "review-1",
            AuditEventType.REVIEW_CREATED,
            "system",
            NOW,
            "created",
        ),
        AuditEvent(
            "evt-2",
            "review-1",
            AuditEventType.REVIEW_STARTED,
            "AI governance",
            later,
            "started",
        ),
        AuditEvent(
            "evt-3",
            "review-1",
            AuditEventType.INFORMATION_REQUESTED,
            "AI governance",
            earlier,
            "requested",
        ),
    )

    with pytest.raises(ValueError, match="chronological"):
        ReviewTrail(case, (), events)
