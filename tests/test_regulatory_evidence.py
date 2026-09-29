import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mailo_cli.regulatory.evidence import (
    EvidenceRecord,
    EvidenceRequirement,
    EvidenceSet,
    EvidenceType,
    load_evidence_set,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "regulatory"
    / "evidence_seed.json"
)
CONTROLS_FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "regulatory"
    / "controls_seed.json"
)


def test_reviewed_evidence_fixture_loads_and_preserves_provenance():
    evidence = load_evidence_set(FIXTURE)

    assert len(evidence.requirements) == 3
    assert len(evidence.records) == 2
    record = evidence.records[0]
    assert record.sha256 == "a" * 64
    assert record.collected_at.utcoffset() is not None
    assert record.source_uri.startswith("https://")


def test_requirement_control_ids_match_reviewed_control_fixture():
    evidence = load_evidence_set(FIXTURE)
    controls = json.loads(CONTROLS_FIXTURE.read_text(encoding="utf-8"))
    control_ids = {item["control_id"] for item in controls["controls"]}

    assert {item.control_id for item in evidence.requirements} <= control_ids


def test_evidence_record_requires_timezone_and_sha256():
    with pytest.raises(ValueError, match="timezone"):
        EvidenceRecord(
            evidence_id="ev-1",
            requirement_id="req-1",
            title="Record",
            evidence_type=EvidenceType.DOCUMENT,
            source_uri="https://example.org/evidence",
            sha256="a" * 64,
            collected_at=datetime(2026, 9, 29, 12, 0),
            owner_role="AI governance",
        )

    with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
        EvidenceRecord(
            evidence_id="ev-2",
            requirement_id="req-1",
            title="Record",
            evidence_type=EvidenceType.DOCUMENT,
            source_uri="https://example.org/evidence",
            sha256="not-a-hash",
            collected_at=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc),
            owner_role="AI governance",
        )


def test_evidence_set_rejects_unknown_requirement():
    record = EvidenceRecord(
        evidence_id="ev-1",
        requirement_id="missing",
        title="Record",
        evidence_type=EvidenceType.DOCUMENT,
        source_uri="https://example.org/evidence",
        sha256="a" * 64,
        collected_at=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc),
        owner_role="AI governance",
    )

    with pytest.raises(ValueError, match="unknown requirement"):
        EvidenceSet(requirements=(), records=(record,))


def test_evidence_set_rejects_type_mismatch():
    requirement = EvidenceRequirement(
        requirement_id="req-1",
        control_id="ctrl-1",
        title="Structured context",
        description="Context export",
        evidence_type=EvidenceType.STRUCTURED_DATA,
    )
    record = EvidenceRecord(
        evidence_id="ev-1",
        requirement_id="req-1",
        title="PDF supplied against structured requirement",
        evidence_type=EvidenceType.DOCUMENT,
        source_uri="https://example.org/evidence",
        sha256="a" * 64,
        collected_at=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc),
        owner_role="AI governance",
    )

    with pytest.raises(ValueError, match="does not match requirement"):
        EvidenceSet(requirements=(requirement,), records=(record,))


def test_missing_record_is_not_materialised_as_failure():
    evidence = load_evidence_set(FIXTURE)

    assert evidence.records_for("evreq-mitigation-record") == ()


def test_round_trip_is_stable():
    evidence = load_evidence_set(FIXTURE)
    decoded = EvidenceSet.from_dict(json.loads(json.dumps(evidence.to_dict())))

    assert decoded == evidence
