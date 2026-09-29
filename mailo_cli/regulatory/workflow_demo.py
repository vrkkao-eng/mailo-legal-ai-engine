"""Fixed end-to-end FRIA workflow scenario for v0.4.4 evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

from .controls import (
    Control,
    ControlImplementationStatus,
    ControlType,
    ObligationControlMapping,
)
from .evidence import EvidenceRecord, EvidenceRequirement, EvidenceSet, EvidenceType
from .impact import ImpactLinkStatus
from .models import ChangeType, RegulatoryChange, SourceLocator
from .obligations import Obligation, ObligationModality
from .review import (
    AuditEvent,
    AuditEventType,
    Escalation,
    HumanResponse,
    ReviewAnswer,
    ReviewCase,
    ReviewDisposition,
    ReviewStatus,
    ReviewTrail,
    route_review_candidate,
)
from .workflow_benchmark import (
    WorkflowBenchmarkReport,
    WorkflowGold,
    WorkflowRouteGold,
    benchmark_workflow,
)
from .workflow_impact import find_evidence_gaps, propagate_regulatory_change


@dataclass(frozen=True, slots=True)
class WorkflowDemoResult:
    """Summary of the deterministic v0.4.4 scenario."""

    change_count: int
    obligation_count: int
    control_count: int
    evidence_requirement_count: int
    evidence_record_count: int
    evidence_gap_count: int
    regulatory_impact_count: int
    route_count: int
    human_review_count: int
    log_only_count: int
    audit_trail_count: int
    benchmark: WorkflowBenchmarkReport
    compliance_determination_produced: bool = False

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["benchmark"] = self.benchmark.to_dict()
        return result


def _scenario_data() -> tuple[
    RegulatoryChange,
    Obligation,
    Control,
    ObligationControlMapping,
    EvidenceSet,
]:
    obligation = Obligation(
        obligation_id="ai-act-art27-fria-review",
        source_id="eu-ai-act",
        locator=SourceLocator("Article 27", paragraph="1"),
        actor="deployer",
        action="perform",
        object="fundamental rights impact assessment",
        modality=ObligationModality.MUST,
        condition="where the Article 27 scope conditions are satisfied",
    )
    control = Control(
        control_id="ctrl-fria-01",
        obligation_id=obligation.obligation_id,
        title="Perform and document FRIA",
        description="Maintain a documented assessment workflow.",
        control_type=ControlType.ASSESSMENT,
        owner_role="AI governance",
        implementation_status=ControlImplementationStatus.NOT_ASSESSED,
        source="reviewed mapping",
    )
    mapping = ObligationControlMapping(
        obligation_id=obligation.obligation_id,
        control_id=control.control_id,
        rationale="Reviewed fixture mapping for the fixed FRIA scenario.",
    )
    requirements = (
        EvidenceRequirement(
            requirement_id="evreq-fria-record",
            control_id=control.control_id,
            title="Documented FRIA record",
            description="Retained FRIA workflow documentation.",
            evidence_type=EvidenceType.DOCUMENT,
        ),
        EvidenceRequirement(
            requirement_id="evreq-deployment-context",
            control_id=control.control_id,
            title="Deployment context record",
            description="Structured deployment context used by the workflow.",
            evidence_type=EvidenceType.STRUCTURED_DATA,
        ),
        EvidenceRequirement(
            requirement_id="evreq-mitigation-record",
            control_id=control.control_id,
            title="Mitigation record",
            description="Documentation of mitigation measures.",
            evidence_type=EvidenceType.DOCUMENT,
        ),
        EvidenceRequirement(
            requirement_id="evreq-supporting-note",
            control_id=control.control_id,
            title="Optional supporting note",
            description="Optional supporting note retained for context.",
            evidence_type=EvidenceType.DOCUMENT,
            mandatory=False,
        ),
    )
    collected = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)
    records = (
        EvidenceRecord(
            evidence_id="ev-fria-2026-001",
            requirement_id="evreq-fria-record",
            title="FRIA assessment record",
            evidence_type=EvidenceType.DOCUMENT,
            source_uri="https://example.org/internal/fria-2026-001",
            sha256="a" * 64,
            collected_at=collected,
            owner_role="AI governance",
        ),
        EvidenceRecord(
            evidence_id="ev-context-2026-001",
            requirement_id="evreq-deployment-context",
            title="Deployment context export",
            evidence_type=EvidenceType.STRUCTURED_DATA,
            source_uri="https://example.org/internal/context-2026-001",
            sha256="b" * 64,
            collected_at=collected,
            owner_role="AI governance",
        ),
    )
    evidence = EvidenceSet(requirements=requirements, records=records)
    change = RegulatoryChange(
        change_id="ai-act-2026-art-27-4-changed",
        change_type=ChangeType.TEXT_CHANGED,
        source_id="eu-ai-act",
        old_version_id="eu-ai-act-2024-08-01",
        new_version_id="eu-ai-act-2026-07-27",
        effective_date=date(2026, 7, 27),
        amendment_source_id="eu-2026-1744",
        amendment_locator=SourceLocator("Article 1", paragraph="13", point="a"),
        source_url="https://eur-lex.europa.eu/eli/reg/2026/1744/oj",
        summary="Reviewed Article 27(4) change used by the fixed scenario.",
        old_locator=SourceLocator("Article 27", paragraph="4"),
        new_locator=SourceLocator("Article 27", paragraph="4"),
    )
    return change, obligation, control, mapping, evidence


def _review_trails(routes: tuple) -> tuple[ReviewTrail, ...]:
    created = datetime(2026, 9, 29, 19, 0, tzinfo=timezone.utc)
    trails: list[ReviewTrail] = []

    for route in routes:
        if route.disposition is not ReviewDisposition.HUMAN_REVIEW:
            continue

        if route.subject_id == "evreq-mitigation-record":
            case = ReviewCase(
                review_id="review-fria-evidence-001",
                route=route,
                status=ReviewStatus.RESOLVED,
                created_at=created,
            )
            response = HumanResponse(
                response_id="resp-fria-evidence-001",
                review_id=case.review_id,
                answer=ReviewAnswer.NO,
                reviewer_role="AI governance",
                rationale=(
                    "The reviewer confirmed that the artefact does not exist "
                    "outside the indexed evidence source."
                ),
                responded_at=created,
            )
            events = (
                AuditEvent(
                    event_id="evt:review-fria-evidence-001:created",
                    review_id=case.review_id,
                    event_type=AuditEventType.REVIEW_CREATED,
                    actor_role="system",
                    occurred_at=created,
                    detail="Focused evidence review created.",
                ),
                AuditEvent(
                    event_id="evt:review-fria-evidence-001:response",
                    review_id=case.review_id,
                    event_type=AuditEventType.RESPONSE_RECORDED,
                    actor_role="AI governance",
                    occurred_at=created,
                    detail="Human response recorded.",
                ),
                AuditEvent(
                    event_id="evt:review-fria-evidence-001:closed",
                    review_id=case.review_id,
                    event_type=AuditEventType.REVIEW_CLOSED,
                    actor_role="AI governance",
                    occurred_at=created,
                    detail="Review case closed after focused response.",
                ),
            )
            trails.append(ReviewTrail(case, (response,), events))
            continue

        case = ReviewCase(
            review_id="review-fria-impact-001",
            route=route,
            status=ReviewStatus.ESCALATED,
            created_at=created,
        )
        response = HumanResponse(
            response_id="resp-fria-impact-001",
            review_id=case.review_id,
            answer=ReviewAnswer.UNKNOWN,
            reviewer_role="Legal",
            rationale=(
                "The effect of the paragraph-level change on the existing "
                "control mapping cannot be determined from the available context."
            ),
            responded_at=created,
        )
        escalation = Escalation(
            escalation_id="esc-fria-impact-001",
            review_id=case.review_id,
            target_role="Senior Legal",
            reason="Interpretive effect remains unresolved.",
            escalated_at=created,
        )
        events = (
            AuditEvent(
                event_id="evt:review-fria-impact-001:created",
                review_id=case.review_id,
                event_type=AuditEventType.REVIEW_CREATED,
                actor_role="system",
                occurred_at=created,
                detail="Focused regulatory-impact review created.",
            ),
            AuditEvent(
                event_id="evt:review-fria-impact-001:response",
                review_id=case.review_id,
                event_type=AuditEventType.RESPONSE_RECORDED,
                actor_role="Legal",
                occurred_at=created,
                detail="UNKNOWN response recorded.",
            ),
            AuditEvent(
                event_id="evt:review-fria-impact-001:escalated",
                review_id=case.review_id,
                event_type=AuditEventType.ESCALATED,
                actor_role="Legal",
                occurred_at=created,
                detail="Interpretive issue escalated.",
            ),
        )
        trails.append(ReviewTrail(case, (response,), events, escalation))

    return tuple(trails)


def run_fixed_workflow_scenario() -> WorkflowDemoResult:
    """Run the deterministic FRIA scenario and benchmark the resulting workflow."""

    change, obligation, control, mapping, evidence = _scenario_data()
    gaps = find_evidence_gaps(evidence)
    impacts = propagate_regulatory_change(
        change,
        obligations=(obligation,),
        mappings=(mapping,),
        controls=(control,),
        evidence=evidence,
    )
    candidates = (*gaps, *impacts)
    routes = tuple(route_review_candidate(candidate) for candidate in candidates)
    trails = _review_trails(routes)

    impact_subject = "ai-act-2026-art-27-4-changed:ctrl-fria-01"
    gold = WorkflowGold(
        routes=(
            WorkflowRouteGold(
                subject_id="evreq-mitigation-record",
                expected_disposition=ReviewDisposition.HUMAN_REVIEW,
                expected_reviewer_role="AI governance",
                expected_context_refs=("evreq-mitigation-record", "ctrl-fria-01"),
            ),
            WorkflowRouteGold(
                subject_id="evreq-supporting-note",
                expected_disposition=ReviewDisposition.LOG_ONLY,
            ),
            WorkflowRouteGold(
                subject_id=impact_subject,
                expected_disposition=ReviewDisposition.HUMAN_REVIEW,
                expected_reviewer_role="Legal",
                expected_context_refs=(
                    "ai-act-2026-art-27-4-changed",
                    "ai-act-art27-fria-review",
                    "ctrl-fria-01",
                ),
            ),
        ),
        expected_audit_subject_ids=(
            "evreq-mitigation-record",
            impact_subject,
        ),
        expected_escalation_subject_ids=(impact_subject,),
    )
    report = benchmark_workflow(routes, trails, gold)

    return WorkflowDemoResult(
        change_count=1,
        obligation_count=1,
        control_count=1,
        evidence_requirement_count=len(evidence.requirements),
        evidence_record_count=len(evidence.records),
        evidence_gap_count=len(gaps),
        regulatory_impact_count=len(impacts),
        route_count=len(routes),
        human_review_count=report.human_review_count,
        log_only_count=report.log_only_count,
        audit_trail_count=len(trails),
        benchmark=report,
    )
