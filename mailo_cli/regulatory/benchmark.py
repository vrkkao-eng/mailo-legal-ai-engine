"""Benchmark deterministic regulatory-change candidates against reviewed records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .diff import StructuralChangeCandidate
from .models import RegulatoryChange
from .reconcile import ReconciliationStatus, reconcile_candidates


@dataclass(frozen=True, slots=True)
class ChangeBenchmarkReport:
    candidate_count: int
    reviewed_count: int
    matched_count: int
    exact_type_count: int
    refined_type_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float
    recall: float
    f1: float
    locator_accuracy: float
    exact_type_accuracy: float
    reviewed_type_coverage: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def benchmark_changes(candidates: Iterable[StructuralChangeCandidate], reviewed_changes: Iterable[RegulatoryChange]) -> ChangeBenchmarkReport:
    candidate_list = tuple(candidates)
    reviewed_list = tuple(reviewed_changes)
    reconciled = reconcile_candidates(candidate_list, reviewed_list)
    exact = sum(item.status is ReconciliationStatus.CONFIRMED for item in reconciled)
    refined = sum(item.status is ReconciliationStatus.TYPE_REFINED for item in reconciled)
    false_positive = sum(item.status is ReconciliationStatus.UNREVIEWED_CANDIDATE for item in reconciled)
    false_negative = sum(item.status is ReconciliationStatus.REVIEWED_ONLY for item in reconciled)
    matched = exact + refined
    precision = _ratio(matched, matched + false_positive)
    recall = _ratio(matched, matched + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    return ChangeBenchmarkReport(
        candidate_count=len(candidate_list), reviewed_count=len(reviewed_list),
        matched_count=matched, exact_type_count=exact, refined_type_count=refined,
        false_positive_count=false_positive, false_negative_count=false_negative,
        precision=precision, recall=recall, f1=f1,
        locator_accuracy=_ratio(matched, len(candidate_list)),
        exact_type_accuracy=_ratio(exact, matched),
        reviewed_type_coverage=_ratio(matched, len(reviewed_list)),
    )
