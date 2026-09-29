"""Traceable change-to-obligation candidate linking."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from .models import RegulatoryChange, SourceLocator
from .obligations import Obligation

class ImpactLinkStatus(str, Enum):
    LOCATOR_MATCH = "locator_match"
    REVIEW_REQUIRED = "review_required"

@dataclass(frozen=True, slots=True)
class ObligationImpactCandidate:
    change_id: str
    obligation_id: str
    status: ImpactLinkStatus
    evidence_locator: SourceLocator
    reason: str
    reviewed: bool = False

def _same_provision(left: SourceLocator, right: SourceLocator) -> bool:
    return left.provision.casefold() == right.provision.casefold()

def link_change_to_obligations(change: RegulatoryChange, obligations: Iterable[Obligation]) -> tuple[ObligationImpactCandidate, ...]:
    """Create conservative review candidates using source and provision identity."""
    locator = change.new_locator or change.old_locator
    if locator is None:
        return ()
    candidates = []
    for obligation in obligations:
        if obligation.source_id != change.source_id or not _same_provision(locator, obligation.locator):
            continue
        exact = locator.canonical.casefold() == obligation.locator.canonical.casefold()
        candidates.append(ObligationImpactCandidate(
            change_id=change.change_id,
            obligation_id=obligation.obligation_id,
            status=ImpactLinkStatus.LOCATOR_MATCH if exact else ImpactLinkStatus.REVIEW_REQUIRED,
            evidence_locator=locator,
            reason=("Reviewed change and obligation share the same canonical locator." if exact else "Reviewed change and obligation share a provision, but their sub-locators differ; human review is required."),
        ))
    return tuple(candidates)
