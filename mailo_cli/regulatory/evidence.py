"""Application-layer evidence requirements and supplied evidence records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import json


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


def _require_https_url(value: str, field_name: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTPS URL")
    return value


class EvidenceType(str, Enum):
    """Evidence categories supported by the v0.4.1 workflow contract."""

    DOCUMENT = "document"
    STRUCTURED_DATA = "structured_data"
    ATTESTATION = "attestation"
    TEST_RESULT = "test_result"
    LOG = "log"
    LINK = "link"


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    """Reviewed organisation-level evidence expectation for one control.

    An evidence requirement is workflow design data. It does not assert that a
    legal source explicitly requires a particular document or artefact.
    """

    requirement_id: str
    control_id: str
    title: str
    description: str
    evidence_type: EvidenceType
    mandatory: bool = True
    source: str = "reviewed control design"

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_type, EvidenceType):
            raise TypeError("evidence_type must be an EvidenceType")
        if type(self.mandatory) is not bool:
            raise TypeError("mandatory must be a bool")
        for field_name in ("requirement_id", "control_id"):
            object.__setattr__(
                self, field_name, _require_identifier(getattr(self, field_name), field_name)
            )
        for field_name in ("title", "description", "source"):
            object.__setattr__(
                self, field_name, _require_text(getattr(self, field_name), field_name)
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "control_id": self.control_id,
            "title": self.title,
            "description": self.description,
            "evidence_type": self.evidence_type.value,
            "mandatory": self.mandatory,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRequirement":
        return cls(
            requirement_id=data["requirement_id"],
            control_id=data["control_id"],
            title=data["title"],
            description=data["description"],
            evidence_type=EvidenceType(data["evidence_type"]),
            mandatory=data.get("mandatory", True),
            source=data.get("source", "reviewed control design"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """A supplied evidence artefact with provenance metadata.

    Presence of an EvidenceRecord means only that an artefact was registered.
    It does not establish sufficiency, validity, freshness, or legal compliance.
    """

    evidence_id: str
    requirement_id: str
    title: str
    evidence_type: EvidenceType
    source_uri: str
    sha256: str
    collected_at: datetime
    owner_role: str

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_type, EvidenceType):
            raise TypeError("evidence_type must be an EvidenceType")
        for field_name in ("evidence_id", "requirement_id"):
            object.__setattr__(
                self, field_name, _require_identifier(getattr(self, field_name), field_name)
            )
        for field_name in ("title", "owner_role"):
            object.__setattr__(
                self, field_name, _require_text(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "source_uri", _require_https_url(self.source_uri, "source_uri")
        )
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
        if not isinstance(self.collected_at, datetime):
            raise TypeError("collected_at must be a datetime")
        if self.collected_at.tzinfo is None or self.collected_at.utcoffset() is None:
            raise ValueError("collected_at must include a timezone offset")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "requirement_id": self.requirement_id,
            "title": self.title,
            "evidence_type": self.evidence_type.value,
            "source_uri": self.source_uri,
            "sha256": self.sha256,
            "collected_at": self.collected_at.isoformat(),
            "owner_role": self.owner_role,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        return cls(
            evidence_id=data["evidence_id"],
            requirement_id=data["requirement_id"],
            title=data["title"],
            evidence_type=EvidenceType(data["evidence_type"]),
            source_uri=data["source_uri"],
            sha256=data["sha256"],
            collected_at=datetime.fromisoformat(data["collected_at"]),
            owner_role=data["owner_role"],
        )


@dataclass(frozen=True, slots=True)
class EvidenceSet:
    """Validated evidence requirements and registered records.

    This collection checks referential and type consistency only. It deliberately
    does not calculate evidence gaps or make sufficiency/compliance decisions.
    """

    requirements: tuple[EvidenceRequirement, ...]
    records: tuple[EvidenceRecord, ...] = ()

    def __post_init__(self) -> None:
        requirement_ids = self._unique_ids(self.requirements, "requirement_id")
        self._unique_ids(self.records, "evidence_id")
        by_id = {item.requirement_id: item for item in self.requirements}

        for record in self.records:
            if record.requirement_id not in requirement_ids:
                raise ValueError(
                    f"evidence {record.evidence_id} references unknown requirement "
                    f"{record.requirement_id}"
                )
            requirement = by_id[record.requirement_id]
            if record.evidence_type is not requirement.evidence_type:
                raise ValueError(
                    f"evidence {record.evidence_id} type {record.evidence_type.value} "
                    f"does not match requirement {record.requirement_id} type "
                    f"{requirement.evidence_type.value}"
                )

    @staticmethod
    def _unique_ids(items: tuple[Any, ...], attribute: str) -> set[str]:
        values = [getattr(item, attribute) for item in items]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {attribute} values are not allowed")
        return set(values)

    def records_for(self, requirement_id: str) -> tuple[EvidenceRecord, ...]:
        requirement_id = _require_identifier(requirement_id, "requirement_id")
        return tuple(
            record for record in self.records if record.requirement_id == requirement_id
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirements": [item.to_dict() for item in self.requirements],
            "records": [item.to_dict() for item in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceSet":
        return cls(
            requirements=tuple(
                EvidenceRequirement.from_dict(item) for item in data["requirements"]
            ),
            records=tuple(EvidenceRecord.from_dict(item) for item in data.get("records", [])),
        )


def load_evidence_set(path: str | Path) -> EvidenceSet:
    """Load and validate a reviewed v0.4.1 evidence fixture."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evidence-set root must be a JSON object")
    return EvidenceSet.from_dict(data)
