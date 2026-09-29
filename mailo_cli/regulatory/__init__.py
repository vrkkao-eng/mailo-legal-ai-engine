"""RegAI application-layer regulatory models and workflow contracts.

This package does not replace the canonical MAILO ontology and does not make
legal-compliance determinations.
"""

from .applicability import ApplicabilityGate, GateOperator, assess_applicability
from .applicability_benchmark import (
    ApplicabilityBenchmarkReport,
    ApplicabilityGold,
    benchmark_applicability,
)
from .benchmark import ChangeBenchmarkReport, benchmark_changes
from .controls import (
    Control,
    ControlImplementationStatus,
    ControlType,
    ObligationControlMapping,
)
from .evidence import (
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceSet,
    EvidenceType,
    load_evidence_set,
)
from .diff import (
    ProvisionUnit,
    StructuralChangeCandidate,
    diff_provisions,
    normalise_text,
    text_sha256,
)
from .impact import ImpactLinkStatus, ObligationImpactCandidate, link_change_to_obligations
from .io import load_change_set
from .models import (
    ChangeType,
    Provision,
    RegulatoryChange,
    RegulatoryChangeSet,
    RegulatorySource,
    RegulatoryVersion,
    SourceLocator,
)
from .obligations import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    Obligation,
    ObligationModality,
    SystemDescription,
)
from .persistence import (
    IdempotencyConflict,
    PersistedWorkflowRun,
    SQLiteWorkflowRepository,
    WorkflowRunNotFound,
)
from .reconcile import ReconciledChange, ReconciliationStatus, reconcile_candidates
from .service import WorkflowEvaluationResult, evaluate_workflow
from .review import (
    AuditEvent,
    AuditEventType,
    Escalation,
    HumanResponse,
    ReviewAnswer,
    ReviewCase,
    ReviewDisposition,
    ReviewQuestion,
    ReviewReasonCode,
    ReviewRoute,
    ReviewStatus,
    ReviewSubjectType,
    ReviewTrail,
    create_review_trail,
    route_review_candidate,
)
from .workflow_benchmark import (
    WorkflowBenchmarkReport,
    WorkflowGold,
    WorkflowRouteGold,
    benchmark_workflow,
)
from .workflow_demo import WorkflowDemoResult, run_fixed_workflow_scenario
from .workflow_impact import (
    EvidenceGapCandidate,
    EvidenceGapStatus,
    RegulatoryImpactCandidate,
    RegulatoryImpactStatus,
    find_evidence_gaps,
    propagate_regulatory_change,
)

__all__ = [
    "ApplicabilityAssessment",
    "ApplicabilityBenchmarkReport",
    "ApplicabilityGate",
    "ApplicabilityGold",
    "ApplicabilityStatus",
    "AuditEvent",
    "AuditEventType",
    "ChangeBenchmarkReport",
    "ChangeType",
    "Control",
    "ControlImplementationStatus",
    "ControlType",
    "EvidenceRecord",
    "EvidenceRequirement",
    "EvidenceSet",
    "EvidenceType",
    "Escalation",
    "EvidenceGapCandidate",
    "EvidenceGapStatus",
    "GateOperator",
    "HumanResponse",
    "IdempotencyConflict",
    "ImpactLinkStatus",
    "Obligation",
    "ObligationControlMapping",
    "ObligationImpactCandidate",
    "ObligationModality",
    "PersistedWorkflowRun",
    "Provision",
    "ProvisionUnit",
    "ReconciledChange",
    "ReconciliationStatus",
    "RegulatoryChange",
    "RegulatoryChangeSet",
    "RegulatorySource",
    "RegulatoryVersion",
    "RegulatoryImpactCandidate",
    "RegulatoryImpactStatus",
    "ReviewAnswer",
    "ReviewCase",
    "ReviewDisposition",
    "ReviewQuestion",
    "ReviewReasonCode",
    "ReviewRoute",
    "ReviewStatus",
    "ReviewSubjectType",
    "ReviewTrail",
    "SourceLocator",
    "StructuralChangeCandidate",
    "SQLiteWorkflowRepository",
    "SystemDescription",
    "WorkflowBenchmarkReport",
    "WorkflowRunNotFound",
    "WorkflowDemoResult",
    "WorkflowEvaluationResult",
    "WorkflowGold",
    "WorkflowRouteGold",
    "assess_applicability",
    "benchmark_applicability",
    "benchmark_changes",
    "benchmark_workflow",
    "create_review_trail",
    "evaluate_workflow",
    "diff_provisions",
    "find_evidence_gaps",
    "link_change_to_obligations",
    "load_change_set",
    "load_evidence_set",
    "normalise_text",
    "propagate_regulatory_change",
    "route_review_candidate",
    "run_fixed_workflow_scenario",
    "reconcile_candidates",
    "text_sha256",
]
