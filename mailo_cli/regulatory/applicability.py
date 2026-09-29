"""Deterministic factual-gate applicability engine."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from .obligations import ApplicabilityAssessment, ApplicabilityStatus, Obligation, SystemDescription

class GateOperator(str, Enum):
    ACTOR_ROLE = "actor_role"
    FACT_PRESENT = "fact_present"
    SYSTEM_KIND = "system_kind"

@dataclass(frozen=True, slots=True)
class ApplicabilityGate:
    gate_id: str
    operator: GateOperator
    expected: str
    description: str

    def __post_init__(self) -> None:
        if not self.gate_id.strip() or not self.expected.strip() or not self.description.strip():
            raise ValueError("gate fields must not be blank")

def _norm(value: str) -> str:
    return " ".join(value.casefold().split())

def _evaluate_gate(gate: ApplicabilityGate, system: SystemDescription) -> bool | None:
    expected=_norm(gate.expected)
    if gate.operator is GateOperator.ACTOR_ROLE:
        return expected in {_norm(role) for role in system.actor_roles}
    if gate.operator is GateOperator.SYSTEM_KIND:
        return _norm(system.system_kind) == expected
    if gate.operator is GateOperator.FACT_PRESENT:
        facts={_norm(fact) for fact in system.facts}
        return True if expected in facts else None
    raise ValueError(f"unsupported gate operator: {gate.operator}")

def assess_applicability(obligation: Obligation, system: SystemDescription, gates: Iterable[ApplicabilityGate]) -> ApplicabilityAssessment:
    """Evaluate reviewed factual gates without inventing missing facts."""
    gate_list=tuple(gates)
    if not gate_list:
        return ApplicabilityAssessment(
            obligation_id=obligation.obligation_id, system_id=system.system_id,
            status=ApplicabilityStatus.REVIEW_REQUIRED,
            reasons=("No reviewed applicability gates were supplied.",),
            missing_facts=("Reviewed applicability gates for this obligation.",),
        )

    reasons=[]; missing=[]
    for gate in gate_list:
        result=_evaluate_gate(gate,system)
        if result is False:
            return ApplicabilityAssessment(
                obligation_id=obligation.obligation_id, system_id=system.system_id,
                status=ApplicabilityStatus.DOES_NOT_APPLY,
                reasons=(f"Gate {gate.gate_id} failed: {gate.description}",),
            )
        if result is None:
            missing.append(gate.description)
        else:
            reasons.append(f"Gate {gate.gate_id} satisfied: {gate.description}")

    if missing:
        return ApplicabilityAssessment(
            obligation_id=obligation.obligation_id, system_id=system.system_id,
            status=ApplicabilityStatus.REVIEW_REQUIRED,
            reasons=tuple(reasons) or ("No supplied fact resolved the reviewed gates.",),
            missing_facts=tuple(missing),
        )
    return ApplicabilityAssessment(
        obligation_id=obligation.obligation_id, system_id=system.system_id,
        status=ApplicabilityStatus.APPLIES,
        reasons=tuple(reasons),
    )
