from pathlib import Path

from mailo_cli.regulatory import ChangeType, SourceLocator, load_change_set
from mailo_cli.regulatory.diff import StructuralChangeCandidate
from mailo_cli.regulatory.reconcile import ReconciliationStatus, reconcile_candidates


FIXTURE = Path(__file__).parents[1] / "examples" / "regulatory" / "ai_act_2026_1744_changes.json"


def _candidate(change_type, old_locator=None, new_locator=None):
    return StructuralChangeCandidate(
        change_type=change_type,
        old_locator=old_locator,
        new_locator=new_locator,
        old_text_sha256="a" * 64 if old_locator else None,
        new_text_sha256="b" * 64 if new_locator else None,
        similarity=0.5 if old_locator and new_locator else None,
    )


def test_reconciliation_confirms_and_refines_reviewed_records():
    reviewed = load_change_set(FIXTURE).changes
    candidates = (
        _candidate(ChangeType.ADDED, new_locator=SourceLocator("Article 4a")),
        _candidate(ChangeType.DELETED, old_locator=SourceLocator("Article 10", paragraph="5")),
        _candidate(ChangeType.TEXT_CHANGED, SourceLocator("Article 27", paragraph="4"), SourceLocator("Article 27", paragraph="4")),
        _candidate(ChangeType.TEXT_CHANGED, SourceLocator("Article 113", point="c"), SourceLocator("Article 113", point="c")),
    )
    results = reconcile_candidates(candidates, reviewed)
    by_id = {item.change_id: item for item in results if item.change_id}

    assert by_id["ai-act-2026-art-4a-added"].status is ReconciliationStatus.CONFIRMED
    assert by_id["ai-act-2026-art-10-5-deleted"].status is ReconciliationStatus.CONFIRMED
    assert by_id["ai-act-2026-art-27-4-changed"].status is ReconciliationStatus.CONFIRMED
    refined = by_id["ai-act-2026-art-113-c-date-change"]
    assert refined.status is ReconciliationStatus.TYPE_REFINED
    assert refined.candidate.change_type is ChangeType.TEXT_CHANGED
    assert refined.reviewed_change.change_type is ChangeType.DATE_CHANGED


def test_unreviewed_candidate_is_not_promoted():
    results = reconcile_candidates(
        (_candidate(ChangeType.TEXT_CHANGED, SourceLocator("Article 99"), SourceLocator("Article 99")),),
        load_change_set(FIXTURE).changes,
    )
    unreviewed = [item for item in results if item.status is ReconciliationStatus.UNREVIEWED_CANDIDATE]
    assert len(unreviewed) == 1
    assert unreviewed[0].reviewed_change is None


def test_reviewed_records_without_candidates_remain_visible():
    results = reconcile_candidates((), load_change_set(FIXTURE).changes)
    assert len(results) == 4
    assert all(item.status is ReconciliationStatus.REVIEWED_ONLY for item in results)
