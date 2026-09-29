"""Evaluation for obligation impact and applicability outcomes."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .obligations import ApplicabilityAssessment, ApplicabilityStatus

@dataclass(frozen=True, slots=True)
class ApplicabilityGold:
    case_id: str
    expected_status: ApplicabilityStatus
    expected_missing_facts: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class ApplicabilityBenchmarkReport:
    case_count: int
    status_correct: int
    status_accuracy: float
    review_case_count: int
    appropriate_abstentions: int
    abstention_accuracy: float
    missing_fact_case_count: int
    missing_fact_complete: int
    missing_fact_completeness: float

def _ratio(a:int,b:int)->float:
    return a/b if b else 0.0

def benchmark_applicability(predictions: Iterable[tuple[str, ApplicabilityAssessment]], gold: Iterable[ApplicabilityGold]) -> ApplicabilityBenchmarkReport:
    pred=dict(predictions); gold_list=tuple(gold)
    status_correct=review_cases=appropriate=missing_cases=missing_complete=0
    for item in gold_list:
        assessment=pred.get(item.case_id)
        if assessment and assessment.status is item.expected_status:
            status_correct+=1
        if item.expected_status is ApplicabilityStatus.REVIEW_REQUIRED:
            review_cases+=1
            if assessment and assessment.status is ApplicabilityStatus.REVIEW_REQUIRED:
                appropriate+=1
        if item.expected_missing_facts:
            missing_cases+=1
            if assessment and set(item.expected_missing_facts).issubset(set(assessment.missing_facts)):
                missing_complete+=1
    return ApplicabilityBenchmarkReport(
        case_count=len(gold_list),status_correct=status_correct,
        status_accuracy=_ratio(status_correct,len(gold_list)),
        review_case_count=review_cases,appropriate_abstentions=appropriate,
        abstention_accuracy=_ratio(appropriate,review_cases),
        missing_fact_case_count=missing_cases,missing_fact_complete=missing_complete,
        missing_fact_completeness=_ratio(missing_complete,missing_cases),
    )
