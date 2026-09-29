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
    "SourceLocator",
    "StructuralChangeCandidate",
    "SystemDescription",
    "assess_applicability",
    "benchmark_applicability",
    "benchmark_changes",
    "diff_provisions",
    "link_change_to_obligations",
    "load_change_set",
    "normalise_text",
    "reconcile_candidates",
    "text_sha256",
]
