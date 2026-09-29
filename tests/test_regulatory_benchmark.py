import json
from pathlib import Path
import pytest
from mailo_cli.regulatory import ChangeType, SourceLocator, load_change_set
from mailo_cli.regulatory.benchmark import benchmark_changes
from mailo_cli.regulatory.diff import StructuralChangeCandidate

ROOT=Path(__file__).parents[1]
GOLD=ROOT/"evals"/"regulatory_change_gold.json"
REVIEWED=ROOT/"examples"/"regulatory"/"ai_act_2026_1744_changes.json"

def _locator(data): return SourceLocator.from_dict(data) if data else None

def _load_candidates():
    data=json.loads(GOLD.read_text(encoding="utf-8"))
    return tuple(StructuralChangeCandidate(change_type=ChangeType(i["change_type"]),old_locator=_locator(i["old_locator"]),new_locator=_locator(i["new_locator"]),old_text_sha256="a"*64 if i["old_locator"] else None,new_text_sha256="b"*64 if i["new_locator"] else None,similarity=0.5 if i["old_locator"] and i["new_locator"] else None) for i in data["candidate_cases"])

def test_gold_benchmark_reports_detection_and_type_refinement():
    r=benchmark_changes(_load_candidates(),load_change_set(REVIEWED).changes)
    assert (r.candidate_count,r.reviewed_count,r.matched_count)==(4,4,4)
    assert (r.exact_type_count,r.refined_type_count)==(3,1)
    assert (r.false_positive_count,r.false_negative_count)==(0,0)
    assert r.precision==pytest.approx(1.0) and r.recall==pytest.approx(1.0) and r.f1==pytest.approx(1.0)
    assert r.locator_accuracy==pytest.approx(1.0)
    assert r.exact_type_accuracy==pytest.approx(0.75)
    assert r.reviewed_type_coverage==pytest.approx(1.0)

def test_benchmark_exposes_false_positive_and_false_negative():
    c=list(_load_candidates()); c.pop()
    c.append(StructuralChangeCandidate(ChangeType.TEXT_CHANGED,SourceLocator("Article 99"),SourceLocator("Article 99"),"a"*64,"b"*64,0.5))
    r=benchmark_changes(c,load_change_set(REVIEWED).changes)
    assert (r.matched_count,r.false_positive_count,r.false_negative_count)==(3,1,1)
    assert r.precision==pytest.approx(0.75) and r.recall==pytest.approx(0.75) and r.f1==pytest.approx(0.75)

def test_empty_benchmark_is_defined():
    r=benchmark_changes((),())
    assert (r.precision,r.recall,r.f1,r.locator_accuracy)==(0.0,0.0,0.0,0.0)
