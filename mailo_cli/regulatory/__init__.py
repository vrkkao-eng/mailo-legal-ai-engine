from .applicability import ApplicabilityGate, GateOperator, assess_applicability
from .benchmark import ChangeBenchmarkReport, benchmark_changes
"""Version-aware regulatory source and change models.

This package is an application-layer representation. It does not replace the
canonical MAILO ontology and does not make legal-compliance determinations.
"""

from .diff import ProvisionUnit, StructuralChangeCandidate, diff_provisions, normalise_text, text_sha256
from .io import load_change_set
from .impact import ImpactLinkStatus, ObligationImpactCandidate, link_change_to_obligations
from .reconcile import ReconciledChange, ReconciliationStatus, reconcile_candidates
from .obligations import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    Obligation,
    ObligationModality,
    SystemDescription,
)
from .models import (
    ChangeType,
    Provision,
    RegulatoryChange,
    RegulatoryChangeSet,
    RegulatorySource,
    RegulatoryVersion,
    SourceLocator,
)

__all__ = [
    "ApplicabilityGate",
    "GateOperator",
    "assess_applicability",
    "ImpactLinkStatus",
    "ObligationImpactCandidate",
    "link_change_to_obligations",
    "ApplicabilityAssessment",
    "ApplicabilityStatus",
    "Obligation",
    "ObligationModality",
    "SystemDescription",
    "ChangeBenchmarkReport",
    "benchmark_changes",
    "ChangeType",
    "ProvisionUnit",
    "StructuralChangeCandidate",
    "diff_provisions",
    "normalise_text",
    "text_sha256",
    "Provision",
    "RegulatoryChange",
    "RegulatoryChangeSet",
    "RegulatorySource",
    "RegulatoryVersion",
    "SourceLocator",
    "load_change_set",
    "ReconciledChange",
    "ReconciliationStatus",
    "reconcile_candidates",
]
