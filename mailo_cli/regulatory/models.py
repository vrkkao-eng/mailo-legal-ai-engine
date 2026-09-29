"""Application-layer models for version-aware regulatory change data."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any
from urllib.parse import urlparse


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_identifier(value: str, field_name: str) -> str:
    value = value.strip()
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} must be a stable identifier")
    return value


def _require_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_url(value: str, field_name: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTPS URL")
    return value


class ChangeType(str, Enum):
    """Change classes supported by the v0.2 regulatory-change model."""

    ADDED = "added"
    DELETED = "deleted"
    TEXT_CHANGED = "text_changed"
    DATE_CHANGED = "date_changed"
    RENUMBERED = "renumbered"


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """Human-readable locator within an official regulatory source."""

    provision: str
    paragraph: str | None = None
    point: str | None = None
    subparagraph: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provision", _require_text(self.provision, "provision"))
        for field_name in ("paragraph", "point", "subparagraph"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, _require_text(value, field_name)
                )

    @property
    def canonical(self) -> str:
        parts = [self.provision]
        if self.paragraph:
            parts.append(f"paragraph {self.paragraph}")
        if self.point:
            parts.append(f"point {self.point}")
        if self.subparagraph:
            parts.append(f"subparagraph {self.subparagraph}")
        return ", ".join(parts)

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceLocator":
        return cls(
            provision=data["provision"],
            paragraph=data.get("paragraph"),
            point=data.get("point"),
            subparagraph=data.get("subparagraph"),
        )


@dataclass(frozen=True, slots=True)
class RegulatorySource:
    """An official regulatory instrument or other versioned legal source."""

    source_id: str
    title: str
    official_url: str
    celex: str | None = None
    jurisdiction: str = "EU"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_id", _require_identifier(self.source_id, "source_id")
        )
        object.__setattr__(self, "title", _require_text(self.title, "title"))
        object.__setattr__(
            self, "official_url", _require_url(self.official_url, "official_url")
        )
        object.__setattr__(
            self, "jurisdiction", _require_text(self.jurisdiction, "jurisdiction")
        )
        if self.celex is not None:
            object.__setattr__(self, "celex", _require_text(self.celex, "celex"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegulatorySource":
        return cls(**data)


@dataclass(frozen=True, slots=True)
class RegulatoryVersion:
    """A validity interval for a selected textual version of a source.

    The interval is half-open: [effective_from, effective_to). This records when
    the selected text is treated as in force for version tracking. It does not
    assert that every obligation in the instrument applies throughout the same
    interval.
    """

    version_id: str
    source_id: str
    label: str
    effective_from: date
    effective_to: date | None = None
    official_url: str | None = None
    sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "version_id", _require_identifier(self.version_id, "version_id")
        )
        object.__setattr__(
            self, "source_id", _require_identifier(self.source_id, "source_id")
        )
        object.__setattr__(self, "label", _require_text(self.label, "label"))
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.official_url is not None:
            object.__setattr__(
                self, "official_url", _require_url(self.official_url, "official_url")
            )
        if self.sha256 is not None and not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")

    def contains(self, when: date) -> bool:
        return self.effective_from <= when and (
            self.effective_to is None or when < self.effective_to
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["effective_from"] = self.effective_from.isoformat()
        result["effective_to"] = (
            self.effective_to.isoformat() if self.effective_to is not None else None
        )
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegulatoryVersion":
        return cls(
            version_id=data["version_id"],
            source_id=data["source_id"],
            label=data["label"],
            effective_from=date.fromisoformat(data["effective_from"]),
            effective_to=(
                date.fromisoformat(data["effective_to"])
                if data.get("effective_to")
                else None
            ),
            official_url=data.get("official_url"),
            sha256=data.get("sha256"),
        )


@dataclass(frozen=True, slots=True)
class Provision:
    """A provision identity within a specific regulatory version."""

    provision_id: str
    version_id: str
    locator: SourceLocator
    source_url: str
    text_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provision_id", _require_identifier(self.provision_id, "provision_id")
        )
        object.__setattr__(
            self, "version_id", _require_identifier(self.version_id, "version_id")
        )
        object.__setattr__(
            self, "source_url", _require_url(self.source_url, "source_url")
        )
        if self.text_sha256 is not None and not _SHA256.fullmatch(self.text_sha256):
            raise ValueError(
                "text_sha256 must contain 64 lowercase hexadecimal characters"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provision_id": self.provision_id,
            "version_id": self.version_id,
            "locator": self.locator.to_dict(),
            "source_url": self.source_url,
            "text_sha256": self.text_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Provision":
        return cls(
            provision_id=data["provision_id"],
            version_id=data["version_id"],
            locator=SourceLocator.from_dict(data["locator"]),
            source_url=data["source_url"],
            text_sha256=data.get("text_sha256"),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryChange:
    """A source-linked change between two selected versions."""

    change_id: str
    change_type: ChangeType
    source_id: str
    old_version_id: str
    new_version_id: str
    effective_date: date
    amendment_source_id: str
    amendment_locator: SourceLocator
    source_url: str
    summary: str
    old_locator: SourceLocator | None = None
    new_locator: SourceLocator | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "change_id",
            "source_id",
            "old_version_id",
            "new_version_id",
            "amendment_source_id",
        ):
            object.__setattr__(
                self, field_name, _require_identifier(getattr(self, field_name), field_name)
            )
        if self.old_version_id == self.new_version_id:
            raise ValueError("old_version_id and new_version_id must differ")
        object.__setattr__(
            self, "source_url", _require_url(self.source_url, "source_url")
        )
        object.__setattr__(self, "summary", _require_text(self.summary, "summary"))

        if self.change_type is ChangeType.ADDED:
            if self.old_locator is not None or self.new_locator is None:
                raise ValueError("added changes require only new_locator")
        elif self.change_type is ChangeType.DELETED:
            if self.old_locator is None or self.new_locator is not None:
                raise ValueError("deleted changes require only old_locator")
        elif self.old_locator is None or self.new_locator is None:
            raise ValueError(
                f"{self.change_type.value} changes require old_locator and new_locator"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "source_id": self.source_id,
            "old_version_id": self.old_version_id,
            "new_version_id": self.new_version_id,
            "effective_date": self.effective_date.isoformat(),
            "amendment_source_id": self.amendment_source_id,
            "amendment_locator": self.amendment_locator.to_dict(),
            "source_url": self.source_url,
            "summary": self.summary,
            "old_locator": self.old_locator.to_dict() if self.old_locator else None,
            "new_locator": self.new_locator.to_dict() if self.new_locator else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegulatoryChange":
        return cls(
            change_id=data["change_id"],
            change_type=ChangeType(data["change_type"]),
            source_id=data["source_id"],
            old_version_id=data["old_version_id"],
            new_version_id=data["new_version_id"],
            effective_date=date.fromisoformat(data["effective_date"]),
            amendment_source_id=data["amendment_source_id"],
            amendment_locator=SourceLocator.from_dict(data["amendment_locator"]),
            source_url=data["source_url"],
            summary=data["summary"],
            old_locator=(
                SourceLocator.from_dict(data["old_locator"])
                if data.get("old_locator")
                else None
            ),
            new_locator=(
                SourceLocator.from_dict(data["new_locator"])
                if data.get("new_locator")
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryChangeSet:
    """Validated collection of sources, versions, provisions, and known changes."""

    sources: tuple[RegulatorySource, ...]
    versions: tuple[RegulatoryVersion, ...]
    changes: tuple[RegulatoryChange, ...]
    provisions: tuple[Provision, ...] = ()

    def __post_init__(self) -> None:
        source_ids = self._unique_ids(self.sources, "source_id")
        version_ids = self._unique_ids(self.versions, "version_id")
        self._unique_ids(self.provisions, "provision_id")
        self._unique_ids(self.changes, "change_id")

        versions_by_id = {item.version_id: item for item in self.versions}
        for version in self.versions:
            if version.source_id not in source_ids:
                raise ValueError(
                    f"version {version.version_id} references unknown source "
                    f"{version.source_id}"
                )

        for provision in self.provisions:
            if provision.version_id not in version_ids:
                raise ValueError(
                    f"provision {provision.provision_id} references unknown version "
                    f"{provision.version_id}"
                )

        for change in self.changes:
            if change.source_id not in source_ids:
                raise ValueError(
                    f"change {change.change_id} references unknown source "
                    f"{change.source_id}"
                )
            if change.amendment_source_id not in source_ids:
                raise ValueError(
                    f"change {change.change_id} references unknown amendment source "
                    f"{change.amendment_source_id}"
                )
            if change.old_version_id not in version_ids or change.new_version_id not in version_ids:
                raise ValueError(
                    f"change {change.change_id} references an unknown version"
                )
            old_version = versions_by_id[change.old_version_id]
            new_version = versions_by_id[change.new_version_id]
            if old_version.source_id != change.source_id or new_version.source_id != change.source_id:
                raise ValueError(
                    f"change {change.change_id} versions must belong to source "
                    f"{change.source_id}"
                )
            if change.effective_date != new_version.effective_from:
                raise ValueError(
                    f"change {change.change_id} effective_date must match the "
                    "new version effective_from date"
                )

    @staticmethod
    def _unique_ids(items: tuple[Any, ...], attribute: str) -> set[str]:
        values = [getattr(item, attribute) for item in items]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {attribute} values are not allowed")
        return set(values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": [item.to_dict() for item in self.sources],
            "versions": [item.to_dict() for item in self.versions],
            "provisions": [item.to_dict() for item in self.provisions],
            "changes": [item.to_dict() for item in self.changes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegulatoryChangeSet":
        return cls(
            sources=tuple(RegulatorySource.from_dict(item) for item in data["sources"]),
            versions=tuple(
                RegulatoryVersion.from_dict(item) for item in data["versions"]
            ),
            provisions=tuple(
                Provision.from_dict(item) for item in data.get("provisions", [])
            ),
            changes=tuple(
                RegulatoryChange.from_dict(item) for item in data["changes"]
            ),
        )
