"""Version-aware regulatory source and change models.

This package is an application-layer representation. It does not replace the
canonical MAILO ontology and does not make legal-compliance determinations.
"""

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

__all__ = [
    "ChangeType",
    "Provision",
    "RegulatoryChange",
    "RegulatoryChangeSet",
    "RegulatorySource",
    "RegulatoryVersion",
    "SourceLocator",
    "load_change_set",
]
