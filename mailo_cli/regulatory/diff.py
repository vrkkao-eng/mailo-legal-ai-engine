"""Deterministic structural diff for normalised regulatory provisions."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from .models import ChangeType, SourceLocator


_WS = re.compile(r"\s+")


def normalise_text(text: str) -> str:
    """Collapse insignificant whitespace while preserving lexical content."""
    return _WS.sub(" ", text).strip()


def text_sha256(text: str) -> str:
    """Hash the normalised provision text for reproducible comparison."""
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProvisionUnit:
    """A pre-parsed structural unit from one regulatory text version."""

    locator: SourceLocator
    text: str

    def __post_init__(self) -> None:
        if not normalise_text(self.text):
            raise ValueError("provision unit text must not be empty")

    @property
    def key(self) -> str:
        return self.locator.canonical.casefold()

    @property
    def normalised_text(self) -> str:
        return normalise_text(self.text)

    @property
    def sha256(self) -> str:
        return text_sha256(self.text)


@dataclass(frozen=True, slots=True)
class StructuralChangeCandidate:
    """A deterministic text/structure candidate, not a legal conclusion."""

    change_type: ChangeType
    old_locator: SourceLocator | None
    new_locator: SourceLocator | None
    old_text_sha256: str | None
    new_text_sha256: str | None
    similarity: float | None = None


def _index(units: Iterable[ProvisionUnit], label: str) -> dict[str, ProvisionUnit]:
    result: dict[str, ProvisionUnit] = {}
    for unit in units:
        if unit.key in result:
            raise ValueError(f"duplicate locator in {label}: {unit.locator.canonical}")
        result[unit.key] = unit
    return result


def diff_provisions(
    old_units: Iterable[ProvisionUnit],
    new_units: Iterable[ProvisionUnit],
) -> tuple[StructuralChangeCandidate, ...]:
    """Compare stable locators and return deterministic structural candidates."""
    old = _index(old_units, "old version")
    new = _index(new_units, "new version")
    candidates: list[StructuralChangeCandidate] = []

    for key in sorted(old.keys() & new.keys()):
        before, after = old[key], new[key]
        if before.sha256 != after.sha256:
            candidates.append(
                StructuralChangeCandidate(
                    change_type=ChangeType.TEXT_CHANGED,
                    old_locator=before.locator,
                    new_locator=after.locator,
                    old_text_sha256=before.sha256,
                    new_text_sha256=after.sha256,
                    similarity=SequenceMatcher(
                        None, before.normalised_text, after.normalised_text
                    ).ratio(),
                )
            )

    for key in sorted(old.keys() - new.keys()):
        before = old[key]
        candidates.append(
            StructuralChangeCandidate(
                change_type=ChangeType.DELETED,
                old_locator=before.locator,
                new_locator=None,
                old_text_sha256=before.sha256,
                new_text_sha256=None,
            )
        )

    for key in sorted(new.keys() - old.keys()):
        after = new[key]
        candidates.append(
            StructuralChangeCandidate(
                change_type=ChangeType.ADDED,
                old_locator=None,
                new_locator=after.locator,
                old_text_sha256=None,
                new_text_sha256=after.sha256,
            )
        )

    order = {
        ChangeType.TEXT_CHANGED: 0,
        ChangeType.DELETED: 1,
        ChangeType.ADDED: 2,
    }
    def sort_key(item: StructuralChangeCandidate) -> tuple[int, str]:
        locator = item.old_locator or item.new_locator
        if locator is None:
            raise ValueError("structural change candidate is missing a locator")
        return order[item.change_type], locator.canonical.casefold()

    return tuple(sorted(candidates, key=sort_key))
