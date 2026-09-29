import pytest

from mailo_cli.regulatory import SourceLocator
from mailo_cli.regulatory.obligations import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    Obligation,
    ObligationModality,
    SystemDescription,
)


def test_reviewed_obligation_represents_actor_action_object_and_conditions():
    obligation = Obligation(
        obligation_id="ai-act-art27-fria-review",
        source_id="eu-ai-act-2024-1689",
        locator=SourceLocator("Article 27", paragraph="1"),
        actor="deployer",
        action="perform",
        object="fundamental rights impact assessment",
        modality=ObligationModality.MUST,
        condition="where scope conditions are satisfied",
        mailo_concept="FundamentalRightsImpactAssessment",
    )
    assert obligation.actor == "deployer"
    assert obligation.modality is ObligationModality.MUST
    assert obligation.locator.canonical == "Article 27, paragraph 1"


def test_system_description_requires_actor_role():
    with pytest.raises(ValueError, match="actor_roles"):
        SystemDescription("sys-1", (), "AI system")


def test_review_required_requires_explicit_missing_facts():
    with pytest.raises(ValueError, match="missing facts"):
        ApplicabilityAssessment(
            obligation_id="obl-1",
            system_id="sys-1",
            status=ApplicabilityStatus.REVIEW_REQUIRED,
            reasons=("Actor role matches but scope is unresolved.",),
        )


def test_review_required_preserves_reason_and_missing_fact():
    assessment = ApplicabilityAssessment(
        obligation_id="obl-1",
        system_id="sys-1",
        status=ApplicabilityStatus.REVIEW_REQUIRED,
        reasons=("Actor role matches but scope is unresolved.",),
        missing_facts=("Whether the system falls within the relevant high-risk category.",),
    )
    assert assessment.status is ApplicabilityStatus.REVIEW_REQUIRED
    assert assessment.missing_facts
