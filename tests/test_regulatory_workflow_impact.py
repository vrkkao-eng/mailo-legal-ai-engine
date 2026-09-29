import json
from datetime import date
from pathlib import Path

from mailo_cli.regulatory.controls import (
    Control,
    ControlImplementationStatus,
    ControlType,
    ObligationControlMapping,
)
from mailo_cli.regulatory.evidence import EvidenceSet, load_evidence_set
from mailo_cli.regulatory.models import (
    ChangeType,
    RegulatoryChange,
    SourceLocator,
)
from mailo_cli.regulatory.obligations import (
    Obligation,
    ObligationModality,
)
from mailo_cli.regulatory.workflow_impact import (
    EvidenceGapStatus,
    RegulatoryImpactStatus,
    find_evidence_gaps,
    propagate_regulatory_change,
)


ROOT = Path(__file__).parents[1]
EVIDENCE_FIXTURE = ROOT / "examples" / "regulatory" / "evidence_seed.json"


def _fria_obligation() -> Obligation:
    return Obligation(
        obligation_id="ai-act-art27-fria-review",
        source_id="eu-ai-act",
        locator=SourceLocator("Article 27", paragraph="1"),
        actor="deployer",
        action="perform",
        object="fundamental rights impact assessment",
        modality=ObligationModality.MUST,
    )


def _fria_control() -> Control:
    return Control(
        control_id="ctrl-fria-01",
        obligation_id="ai-act-art27-fria-review",
        title="Perform and document FRIA",
        description="Maintain a documented FRIA workflow.",
        control_type=ControlType.ASSESSMENT,
        owner_role="AI governance",
        implementation_status=ControlImplementationStatus.NOT_ASSESSED,
        source="reviewed mapping",
    )


def _fria_mapping() -> ObligationControlMapping:
    return ObligationControlMapping(
        obligation_id="ai-act-art27-fria-review",
        control_id="ctrl-fria-01",
        rationale="Reviewed mapping for the FRIA workflow.",
    )


def _article27_change() -> RegulatoryChange:
    return RegulatoryChange(
        change_id="ai-act-2026-art-27-4-changed",
        change_type=ChangeType.TEXT_CHANGED,
        source_id="eu-ai-act",
        old_version_id="old",
        new_version_id="new",
        effective_date=date(2026, 7, 27),
        amendment_source_id="eu-2026-1744",
        amendment_locator=SourceLocator("Article 1", paragraph="13", point="a"),
        source_url="https://example.org/source",
        summary="Reviewed Article 27 change.",
        old_locator=SourceLocator("Article 27", paragraph="4"),
        new_locator=SourceLocator("Article 27", paragraph="4"),
    )


def test_find_evidence_gaps_returns_only_missing_registered_records():
    evidence = load_evidence_set(EVIDENCE_FIXTURE)

    gaps = find_evidence_gaps(evidence)

    assert len(gaps) == 1
    assert gaps[0].requirement_id == "evreq-mitigation-record"
    assert gaps[0].control_id == "ctrl-fria-01"
    assert gaps[0].status is EvidenceGapStatus.MANDATORY_NO_RECORD
    assert "No registered evidence record" in gaps[0].reason


def test_optional_requirement_without_record_is_not_treated_as_failure():
    raw = json.loads(EVIDENCE_FIXTURE.read_text(encoding="utf-8"))
    raw["requirements"][-1]["mandatory"] = False
    evidence = EvidenceSet.from_dict(raw)

    gaps = find_evidence_gaps(evidence)

    assert gaps[0].status is EvidenceGapStatus.OPTIONAL_NO_RECORD


def test_regulatory_change_propagates_to_control_and_requirements():
    evidence = load_evidence_set(EVIDENCE_FIXTURE)

    result = propagate_regulatory_change(
        _article27_change(),
        obligations=(_fria_obligation(),),
        mappings=(_fria_mapping(),),
        controls=(_fria_control(),),
        evidence=evidence,
    )

    assert len(result) == 1
    candidate = result[0]
    assert candidate.change_id == "ai-act-2026-art-27-4-changed"
    assert candidate.obligation_id == "ai-act-art27-fria-review"
    assert candidate.control_id == "ctrl-fria-01"
    assert candidate.requirement_ids == (
        "evreq-deployment-context",
        "evreq-fria-record",
        "evreq-mitigation-record",
    )
    assert candidate.status is RegulatoryImpactStatus.REVIEW_REQUIRED


def test_same_article_different_paragraph_still_requires_downstream_review():
    evidence = load_evidence_set(EVIDENCE_FIXTURE)

    result = propagate_regulatory_change(
        _article27_change(),
        obligations=(_fria_obligation(),),
        mappings=(_fria_mapping(),),
        controls=(_fria_control(),),
        evidence=evidence,
    )

    assert result[0].upstream_link_status.value == "review_required"


def test_missing_reviewed_mapping_preserves_obligation_level_review_candidate():
    evidence = load_evidence_set(EVIDENCE_FIXTURE)

    result = propagate_regulatory_change(
        _article27_change(),
        obligations=(_fria_obligation(),),
        mappings=(),
        controls=(_fria_control(),),
        evidence=evidence,
    )

    assert len(result) == 1
    assert result[0].control_id is None
    assert result[0].requirement_ids == ()
    assert "no reviewed obligation-to-control mapping" in result[0].reason


def test_propagation_rejects_inconsistent_mapping():
    evidence = load_evidence_set(EVIDENCE_FIXTURE)
    wrong_control = Control(
        control_id="ctrl-fria-01",
        obligation_id="other-obligation",
        title="Control",
        description="Description",
        control_type=ControlType.ASSESSMENT,
        owner_role="AI governance",
    )

    try:
        propagate_regulatory_change(
            _article27_change(),
            obligations=(_fria_obligation(),),
            mappings=(_fria_mapping(),),
            controls=(wrong_control,),
            evidence=evidence,
        )
    except ValueError as exc:
        assert "obligation does not match mapping" in str(exc)
    else:
        raise AssertionError("expected inconsistent mapping to be rejected")


def test_repo_fixtures_share_ai_act_identity_for_propagation():
    changes = json.loads(
        (ROOT / "examples" / "regulatory" / "ai_act_2026_1744_changes.json").read_text(
            encoding="utf-8"
        )
    )
    obligations = json.loads(
        (ROOT / "examples" / "regulatory" / "obligations_seed.json").read_text(
            encoding="utf-8"
        )
    )

    article27_change = next(
        item for item in changes["changes"]
        if item["change_id"] == "ai-act-2026-art-27-4-changed"
    )
    fria_obligation = obligations["obligations"][0]

    assert article27_change["source_id"] == "eu-ai-act"
    assert fria_obligation["source_id"] == article27_change["source_id"]
