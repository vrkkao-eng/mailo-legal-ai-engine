import pytest
from mailo_cli.regulatory.applicability_benchmark import ApplicabilityGold, benchmark_applicability
from mailo_cli.regulatory.obligations import ApplicabilityAssessment, ApplicabilityStatus

def _assessment(status, missing=()):
    return ApplicabilityAssessment("obl","sys",status,("evaluated",),missing)

def test_benchmark_measures_status_abstention_and_missing_facts():
    gold=(
        ApplicabilityGold("applies",ApplicabilityStatus.APPLIES),
        ApplicabilityGold("no",ApplicabilityStatus.DOES_NOT_APPLY),
        ApplicabilityGold("review",ApplicabilityStatus.REVIEW_REQUIRED,("public-body status",)),
    )
    predictions=(
        ("applies",_assessment(ApplicabilityStatus.APPLIES)),
        ("no",_assessment(ApplicabilityStatus.DOES_NOT_APPLY)),
        ("review",_assessment(ApplicabilityStatus.REVIEW_REQUIRED,("public-body status",))),
    )
    r=benchmark_applicability(predictions,gold)
    assert r.status_accuracy==pytest.approx(1.0)
    assert r.abstention_accuracy==pytest.approx(1.0)
    assert r.missing_fact_completeness==pytest.approx(1.0)

def test_wrong_binary_answer_penalises_abstention():
    gold=(ApplicabilityGold("review",ApplicabilityStatus.REVIEW_REQUIRED,("classification",)),)
    predictions=(("review",_assessment(ApplicabilityStatus.APPLIES)),)
    r=benchmark_applicability(predictions,gold)
    assert r.status_accuracy==0.0
    assert r.abstention_accuracy==0.0
    assert r.missing_fact_completeness==0.0

def test_empty_benchmark_is_defined():
    r=benchmark_applicability((),())
    assert r.status_accuracy==0.0
    assert r.abstention_accuracy==0.0
