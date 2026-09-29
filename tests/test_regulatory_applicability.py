from mailo_cli.regulatory import SourceLocator
from mailo_cli.regulatory.applicability import ApplicabilityGate, GateOperator, assess_applicability
from mailo_cli.regulatory.obligations import ApplicabilityStatus, Obligation, ObligationModality, SystemDescription

def _obligation():
    return Obligation("obl-1","eu-ai-act",SourceLocator("Article 27"),"deployer","perform","FRIA",ObligationModality.MUST)

def test_all_reviewed_gates_satisfied_means_applies():
    system=SystemDescription("sys-1",("deployer",),"high-risk AI system",("public body deployer",))
    gates=(ApplicabilityGate("actor",GateOperator.ACTOR_ROLE,"deployer","System actor role is deployer."),ApplicabilityGate("kind",GateOperator.SYSTEM_KIND,"high-risk AI system","System is in the reviewed system category."),ApplicabilityGate("fact",GateOperator.FACT_PRESENT,"public body deployer","Deployment context fact is present."))
    result=assess_applicability(_obligation(),system,gates)
    assert result.status is ApplicabilityStatus.APPLIES
    assert not result.missing_facts

def test_failed_closed_world_gate_means_does_not_apply():
    system=SystemDescription("sys-1",("provider",),"high-risk AI system")
    gate=ApplicabilityGate("actor",GateOperator.ACTOR_ROLE,"deployer","System actor role is deployer.")
    result=assess_applicability(_obligation(),system,(gate,))
    assert result.status is ApplicabilityStatus.DOES_NOT_APPLY

def test_absent_open_world_fact_requires_review():
    system=SystemDescription("sys-1",("deployer",),"high-risk AI system")
    gate=ApplicabilityGate("fact",GateOperator.FACT_PRESENT,"public body deployer","Whether deployment is by a public body.")
    result=assess_applicability(_obligation(),system,(gate,))
    assert result.status is ApplicabilityStatus.REVIEW_REQUIRED
    assert result.missing_facts==("Whether deployment is by a public body.",)

def test_no_reviewed_gates_requires_review():
    system=SystemDescription("sys-1",("deployer",),"AI system")
    result=assess_applicability(_obligation(),system,())
    assert result.status is ApplicabilityStatus.REVIEW_REQUIRED
    assert result.missing_facts
