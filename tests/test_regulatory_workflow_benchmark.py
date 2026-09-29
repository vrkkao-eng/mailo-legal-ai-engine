import pytest

from mailo_cli.regulatory.review import (
    ReviewDisposition,
    ReviewReasonCode,
    ReviewRoute,
    ReviewSubjectType,
)
from mailo_cli.regulatory.workflow_benchmark import (
    WorkflowGold,
    WorkflowRouteGold,
    benchmark_workflow,
)
from mailo_cli.regulatory.workflow_demo import run_fixed_workflow_scenario


def test_fixed_workflow_scenario_is_end_to_end_and_safe():
    result = run_fixed_workflow_scenario()
    report = result.benchmark

    assert result.change_count == 1
    assert result.obligation_count == 1
    assert result.control_count == 1
    assert result.evidence_requirement_count == 4
    assert result.evidence_record_count == 2
    assert result.evidence_gap_count == 2
    assert result.regulatory_impact_count == 1
    assert result.route_count == 3
    assert result.human_review_count == 2
    assert result.log_only_count == 1
    assert result.audit_trail_count == 2
    assert result.compliance_determination_produced is False

    assert report.routing_accuracy == pytest.approx(1.0)
    assert report.traceability_completeness == pytest.approx(1.0)
    assert report.human_review_share == pytest.approx(2 / 3)
    assert report.audit_trace_completeness == pytest.approx(1.0)
    assert report.escalation_integrity_rate == pytest.approx(1.0)
    assert report.unsafe_unknown_resolutions == 0
    assert report.burden_proxy_mean_context_refs > 0
    assert report.burden_proxy_mean_question_chars > 0


def test_workflow_benchmark_penalises_wrong_routing():
    route = ReviewRoute(
        subject_type=ReviewSubjectType.EVIDENCE_GAP,
        subject_id="optional-gap",
        disposition=ReviewDisposition.LOG_ONLY,
        reason_code=ReviewReasonCode.OPTIONAL_EVIDENCE_NOT_REGISTERED,
    )
    gold = WorkflowGold(
        routes=(
            WorkflowRouteGold(
                subject_id="optional-gap",
                expected_disposition=ReviewDisposition.HUMAN_REVIEW,
                expected_reviewer_role="AI governance",
            ),
        )
    )

    report = benchmark_workflow((route,), (), gold)

    assert report.routing_accuracy == 0.0
    assert report.human_review_share == 0.0


def test_workflow_benchmark_counts_missing_route_as_incomplete():
    gold = WorkflowGold(
        routes=(
            WorkflowRouteGold(
                subject_id="missing",
                expected_disposition=ReviewDisposition.LOG_ONLY,
            ),
        )
    )

    report = benchmark_workflow((), (), gold)

    assert report.routing_accuracy == 0.0
    assert report.traceability_completeness == 0.0


def test_empty_workflow_benchmark_is_defined():
    report = benchmark_workflow((), (), WorkflowGold(routes=()))

    assert report.routing_accuracy == 0.0
    assert report.traceability_completeness == 0.0
    assert report.human_review_share == 0.0
    assert report.audit_trace_completeness == 0.0
    assert report.escalation_integrity_rate == 0.0
