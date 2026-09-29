"""Reconcile deterministic structural candidates with reviewed change records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .diff import StructuralChangeCandidate
from .models import ChangeType, RegulatoryChange, SourceLocator


class ReconciliationStatus(str, Enum):
    CONFIRMED = "confirmed"
    TYPE_REFINED = "type_refined"
    UNREVIEWED_CANDIDATE = "unreviewed_candidate"
    REVIEWED_ONLY = "reviewed_only"


@dataclass(frozen=True, slots=True)
class ReconciledChange:
    status: ReconciliationStatus
    candidate: StructuralChangeCandidate | None
    reviewed_change: RegulatoryChange | None
    note: str

    @property
    def change_id(self) -> str | None:
        return self.reviewed_change.change_id if self.reviewed_change else None


def _locator_key(locator: SourceLocator | None) -> str | None:
    return locator.canonical.casefold() if locator else None


def _candidate_key(candidate: StructuralChangeCandidate) -> tuple[str | None, str | None]:
    return (_locator_key(candidate.old_locator), _locator_key(candidate.new_locator))


def _reviewed_key(change: RegulatoryChange) -> tuple[str | None, str | None]:
    return (_locator_key(change.old_locator), _locator_key(change.new_locator))


def _types_compatible(candidate: ChangeType, reviewed: ChangeType) -> bool:
    if candidate is reviewed:
        return True
    return candidate is ChangeType.TEXT_CHANGED and reviewed is ChangeType.DATE_CHANGED


def reconcile_candidates(
    candidates: Iterable[StructuralChangeCandidate],
    reviewed_changes: Iterable[RegulatoryChange],
) -> tuple[ReconciledChange, ...]:
    """Match structural candidates to reviewed records by old/new locator pair."""
    reviewed_list = tuple(reviewed_changes)
    reviewed_by_key: dict[tuple[str | None, str | None], RegulatoryChange] = {}

    for change in reviewed_list:
        key = _reviewed_key(change)
        if key in reviewed_by_key:
            raise ValueError(f"duplicate reviewed locator pair: {key}")
        reviewed_by_key[key] = change

    matched_ids: set[str] = set()
    results: list[ReconciledChange] = []

    for candidate in candidates:
        reviewed = reviewed_by_key.get(_candidate_key(candidate))
        if reviewed is None or not _types_compatible(candidate.change_type, reviewed.change_type):
            results.append(ReconciledChange(
                status=ReconciliationStatus.UNREVIEWED_CANDIDATE,
                candidate=candidate,
                reviewed_change=None,
                note="Structural candidate has no compatible reviewed change record.",
            ))
            continue

        matched_ids.add(reviewed.change_id)
        refined = candidate.change_type is not reviewed.change_type
        results.append(ReconciledChange(
            status=ReconciliationStatus.TYPE_REFINED if refined else ReconciliationStatus.CONFIRMED,
            candidate=candidate,
            reviewed_change=reviewed,
            note=(
                "Reviewed source metadata refines the structural text change to "
                f"{reviewed.change_type.value}."
                if refined
                else "Structural candidate is confirmed by reviewed source metadata."
            ),
        ))

    for reviewed in reviewed_list:
        if reviewed.change_id not in matched_ids:
            results.append(ReconciledChange(
                status=ReconciliationStatus.REVIEWED_ONLY,
                candidate=None,
                reviewed_change=reviewed,
                note="Reviewed change is not represented by the supplied structural candidates.",
            ))

    return tuple(results)
