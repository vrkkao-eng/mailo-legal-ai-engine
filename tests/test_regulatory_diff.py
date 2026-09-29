import json
from pathlib import Path

import pytest

from mailo_cli.regulatory import ChangeType, SourceLocator
from mailo_cli.regulatory.diff import ProvisionUnit, diff_provisions, normalise_text


EXAMPLES = Path(__file__).parents[1] / "examples" / "regulatory"


def _load_units(name: str) -> list[ProvisionUnit]:
    data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    return [
        ProvisionUnit(locator=SourceLocator.from_dict(item["locator"]), text=item["text"])
        for item in data
    ]


def test_structural_diff_detects_added_deleted_and_changed_units():
    changes = diff_provisions(
        _load_units("structural_diff_old.json"),
        _load_units("structural_diff_new.json"),
    )
    assert [(item.change_type, (item.old_locator or item.new_locator).canonical) for item in changes] == [
        (ChangeType.TEXT_CHANGED, "Article 27, paragraph 4"),
        (ChangeType.DELETED, "Article 10, paragraph 5"),
        (ChangeType.ADDED, "Article 4a"),
    ]
    assert changes[0].similarity is not None
    assert 0.0 <= changes[0].similarity < 1.0
    assert changes[1].new_text_sha256 is None
    assert changes[2].old_text_sha256 is None


def test_whitespace_only_changes_are_ignored():
    old = [ProvisionUnit(SourceLocator("Article 1"), "A   legal\ntext.")]
    new = [ProvisionUnit(SourceLocator("Article 1"), " A legal text. ")]
    assert normalise_text(old[0].text) == normalise_text(new[0].text)
    assert diff_provisions(old, new) == ()


def test_duplicate_locators_are_rejected():
    units = [
        ProvisionUnit(SourceLocator("Article 1"), "first"),
        ProvisionUnit(SourceLocator("Article 1"), "second"),
    ]
    with pytest.raises(ValueError, match="duplicate locator"):
        diff_provisions(units, [])
