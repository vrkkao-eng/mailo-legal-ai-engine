"""Application service for stateless RegAI workflow evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .controls import Control, ObligationControlMapping
from .evidence import EvidenceSet
from .models import RegulatoryChange
from .obligations import Obligation
from .review import ReviewRoute, route_review_candidate
from .workflow_impact import (
    EvidenceGapCandidate,
    RegulatoryImpactCandidate,
    find_evidence_gaps,
    propagate_regulatory_change,
)


def _gap_to_dict(item: EvidenceGapCandidate) -> dict[str, object]:
    return {
        "requirement_id": item.requirement_id,
        "control_id": item.control_id,
        "status": item.status.value,
        "reason": item.reason,
    }


def _impact_to_dict(item: RegulatoryImpactCandidate) -> dict[str, object]:
    return {
        "change_id": item.change_id,
        "obligation_id": item.obligation_id,
        "control_id": item.control_id,
        "requirement_ids": list(item.requirement_ids),
        "upstream_link_status": item.upstream_link_status.value,
        "status": item.status.value,
        "reason": item.reason,
    }


def _route_to_dict(item: ReviewRoute) -> dict[str, object]:
    question = None
    if item.question is not None:
        question = {
            "question_id": item.question.question_id,
            "prompt": item.question.prompt,
            "permitted_answers": [
                answer.value for answer in item.question.permitted_answers
            ],
            "context_refs": list(item.question.context_refs),
        }
    return {
        "subject_type": item.subject_type.value,
        "subject_id": item.subject_id,
        "disposition": item.disposition.value,
        "reason_code": item.reason_code.value,
        "reviewer_role": item.reviewer_role,
        "question": question,
    }


@dataclass(frozen=True, slots=True)
class WorkflowEvaluationResult:
    """Deterministic stateless workflow output for one reviewed change."""

    evidence_gaps: tuple[EvidenceGapCandidate, ...]
    regulatory_impacts: tuple[RegulatoryImpactCandidate, ...]
    review_routes: tuple[ReviewRoute, ...]
    compliance_determination_produced: bool = False

    def to_dict(self) -> dict[str, object]:
        human_review_count = sum(
            route.disposition.value == "human_review" for route in self.review_routes
        )
        log_only_count = sum(
            route.disposition.value == "log_only" for route in self.review_routes
        )
        return {
            "summary": {
                "evidence_gap_count": len(self.evidence_gaps),
                "regulatory_impact_count": len(self.regulatory_impacts),
                "route_count": len(self.review_routes),
                "human_review_count": human_review_count,
                "log_only_count": log_only_count,
            },
            "evidence_gaps": [_gap_to_dict(item) for item in self.evidence_gaps],
            "regulatory_impacts": [
                _impact_to_dict(item) for item in self.regulatory_impacts
            ],
            "review_routes": [_route_to_dict(item) for item in self.review_routes],
            "compliance_determination_produced": (
                self.compliance_determination_produced
            ),
        }


def evaluate_workflow(
    change: RegulatoryChange,
    obligations: Iterable[Obligation],
    mappings: Iterable[ObligationControlMapping],
    controls: Iterable[Control],
    evidence: EvidenceSet,
) -> WorkflowEvaluationResult:
    """Evaluate one reviewed change against supplied organisation workflow data.

    This service is stateless. It produces review candidates and routes only; it
    does not persist review cases, mutate controls, or make legal-compliance
    determinations.
    """

    obligation_items = tuple(obligations)
    mapping_items = tuple(mappings)
    control_items = tuple(controls)

    gaps = find_evidence_gaps(evidence)
    impacts = propagate_regulatory_change(
        change,
        obligations=obligation_items,
        mappings=mapping_items,
        controls=control_items,
        evidence=evidence,
    )
    candidates: tuple[
        EvidenceGapCandidate | RegulatoryImpactCandidate, ...
    ] = (*gaps, *impacts)
    routes = tuple(route_review_candidate(candidate) for candidate in candidates)

    return WorkflowEvaluationResult(
        evidence_gaps=gaps,
        regulatory_impacts=impacts,
        review_routes=routes,
    )
