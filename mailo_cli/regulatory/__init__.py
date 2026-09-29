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
from .reconcile import ReconciledChange, ReconciliationStatus, reconcile_candidates
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
    "ChangeBenchmarkReport",
    "ChangeType",
    "Control",
    "ControlImplementationStatus",
    "ControlType",
    "EvidenceRecord",
    "EvidenceRequirement",
    "EvidenceSet",
    "EvidenceType",
    "EvidenceGapCandidate",
    "EvidenceGapStatus",
    "GateOperator",
    "ImpactLinkStatus",
    "Obligation",
    "ObligationControlMapping",
    "ObligationImpactCandidate",
    "ObligationModality",
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
    "SourceLocator",
    "StructuralChangeCandidate",
    "SystemDescription",
    "assess_applicability",
    "benchmark_applicability",
    "benchmark_changes",
    "diff_provisions",
    "find_evidence_gaps",
    "link_change_to_obligations",
    "load_change_set",
    "load_evidence_set",
    "normalise_text",
    "propagate_regulatory_change",
    "reconcile_candidates",
    "text_sha256",
]
