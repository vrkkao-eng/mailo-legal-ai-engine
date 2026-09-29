import pytest

from mailo_cli.regulatory.controls import (
    Control,
    ControlImplementationStatus,
    ControlType,
    ObligationControlMapping,
)


def test_control_defaults_to_not_assessed():
    control = Control(
        control_id="ctrl-fria-01",
        obligation_id="ai-act-art27-fria-review",
        title="Perform and document FRIA",
        description="Maintain an organisation-owned control for the reviewed FRIA obligation.",
        control_type=ControlType.ASSESSMENT,
        owner_role="AI governance",
        source="reviewed mapping",
    )
    assert control.implementation_status is ControlImplementationStatus.NOT_ASSESSED


def test_control_rejects_blank_owner():
    with pytest.raises(ValueError, match="owner_role"):
        Control(
            control_id="ctrl-1",
            obligation_id="obl-1",
            title="Control",
            description="Description",
            control_type=ControlType.GOVERNANCE,
            owner_role=" ",
        )


def test_mapping_requires_human_review():
    with pytest.raises(ValueError, match="reviewed"):
        ObligationControlMapping(
            obligation_id="obl-1",
            control_id="ctrl-1",
            rationale="candidate only",
            reviewed=False,
        )


def test_reviewed_mapping_preserves_ids_and_rationale():
    mapping = ObligationControlMapping(
        obligation_id="ai-act-art27-fria-review",
        control_id="ctrl-fria-01",
        rationale="Reviewed application-layer mapping for the seed scenario.",
    )
    assert mapping.reviewed is True
    assert mapping.control_id == "ctrl-fria-01"
