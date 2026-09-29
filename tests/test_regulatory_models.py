import json
from datetime import date
from pathlib import Path

import pytest

from mailo_cli.regulatory import (
    ChangeType,
    RegulatoryChange,
    RegulatoryChangeSet,
    RegulatorySource,
    RegulatoryVersion,
    SourceLocator,
    load_change_set,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "regulatory"
    / "ai_act_2026_1744_changes.json"
)


def test_reviewed_ai_act_fixture_loads_and_is_version_consistent():
    change_set = load_change_set(FIXTURE)

    assert {source.source_id for source in change_set.sources} == {
        "eu-ai-act",
        "eu-2026-1744",
    }
    assert len(change_set.changes) == 4
    assert {change.change_type for change in change_set.changes} == {
        ChangeType.ADDED,
        ChangeType.DELETED,
        ChangeType.TEXT_CHANGED,
        ChangeType.DATE_CHANGED,
    }
    assert all(
        change.effective_date == date(2026, 7, 27)
        for change in change_set.changes
    )


def test_regulatory_versions_use_half_open_intervals():
    change_set = load_change_set(FIXTURE)
    versions = {item.version_id: item for item in change_set.versions}

    old = versions["eu-ai-act-2024-08-01"]
    new = versions["eu-ai-act-2026-07-27"]

    assert old.contains(date(2026, 7, 26))
    assert not old.contains(date(2026, 7, 27))
    assert new.contains(date(2026, 7, 27))


def test_added_and_deleted_changes_enforce_locator_direction():
    common = dict(
        source_id="eu-ai-act",
        old_version_id="old",
        new_version_id="new",
        effective_date=date(2026, 7, 27),
        amendment_source_id="eu-2026-1744",
        amendment_locator=SourceLocator("Article 1", paragraph="6"),
        source_url="https://eur-lex.europa.eu/eli/reg/2026/1744/oj",
        summary="Synthetic test change",
    )

    with pytest.raises(ValueError, match="added changes require only new_locator"):
        RegulatoryChange(
            change_id="bad-added",
            change_type=ChangeType.ADDED,
            old_locator=SourceLocator("Article 3"),
            new_locator=SourceLocator("Article 4a"),
            **common,
        )

    with pytest.raises(ValueError, match="deleted changes require only old_locator"):
        RegulatoryChange(
            change_id="bad-deleted",
            change_type=ChangeType.DELETED,
            old_locator=SourceLocator("Article 10", paragraph="5"),
            new_locator=SourceLocator("Article 4a"),
            **common,
        )


def test_change_set_rejects_duplicate_ids_and_cross_source_versions():
    source_a = RegulatorySource(
        source_id="source-a",
        title="A",
        official_url="https://example.org/a",
    )
    source_b = RegulatorySource(
        source_id="source-b",
        title="B",
        official_url="https://example.org/b",
    )
    old = RegulatoryVersion(
        version_id="a-old",
        source_id="source-a",
        label="old",
        effective_from=date(2025, 1, 1),
        effective_to=date(2026, 1, 1),
    )
    new_wrong_source = RegulatoryVersion(
        version_id="b-new",
        source_id="source-b",
        label="new",
        effective_from=date(2026, 1, 1),
    )
    change = RegulatoryChange(
        change_id="change-1",
        change_type=ChangeType.TEXT_CHANGED,
        source_id="source-a",
        old_version_id="a-old",
        new_version_id="b-new",
        effective_date=date(2026, 1, 1),
        amendment_source_id="source-b",
        amendment_locator=SourceLocator("Article 1"),
        source_url="https://example.org/amendment",
        summary="Synthetic",
        old_locator=SourceLocator("Article 2"),
        new_locator=SourceLocator("Article 2"),
    )

    with pytest.raises(ValueError, match="versions must belong to source source-a"):
        RegulatoryChangeSet(
            sources=(source_a, source_b),
            versions=(old, new_wrong_source),
            changes=(change,),
        )

    with pytest.raises(ValueError, match="duplicate source_id"):
        RegulatoryChangeSet(
            sources=(source_a, source_a),
            versions=(),
            changes=(),
        )


def test_fixture_round_trip_is_stable():
    change_set = load_change_set(FIXTURE)
    encoded = json.loads(json.dumps(change_set.to_dict()))
    decoded = RegulatoryChangeSet.from_dict(encoded)

    assert decoded == change_set
    assert decoded.changes[0].new_locator.canonical == "Article 4a"
