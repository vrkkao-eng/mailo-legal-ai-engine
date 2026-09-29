"""Evidence-gap detection and reviewed regulatory-impact propagation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from collections.abc import Callable, Iterable
from typing import TypeVar

from .controls import Control, ObligationControlMapping
from .evidence import EvidenceSet
from .impact import ImpactLinkStatus, link_change_to_obligations
from .models import RegulatoryChange
from .obligations import Obligation


class EvidenceGapStatus(str, Enum):
    """Absence states for registered evidence records."""

    MANDATORY_NO_RECORD = "mandatory_no_record"
    OPTIONAL_NO_RECORD = "optional_no_record"


@dataclass(frozen=True, slots=True)
class EvidenceGapCandidate:
    """A missing registered record for one reviewed evidence requirement.

    This is an inventory observation only. It does not establish that evidence
    does not exist, that a control failed, or that an organisation is
    non-compliant.
    """

    requirement_id: str
    control_id: str
    status: EvidenceGapStatus
    reason: str


class RegulatoryImpactStatus(str, Enum):
    """Downstream workflow status after an upstream reviewed legal change."""

    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class RegulatoryImpactCandidate:
    """Traceable downstream review candidate caused by a regulatory change.

    The candidate preserves the upstream change-to-obligation link and any
    reviewed obligation-to-control mapping. It is not a determination that a
    control or evidence requirement is obsolete, deficient, or non-compliant.
    """

    change_id: str
    obligation_id: str
    control_id: str | None
    requirement_ids: tuple[str, ...]
    upstream_link_status: ImpactLinkStatus
    status: RegulatoryImpactStatus
    reason: str


def find_evidence_gaps(evidence: EvidenceSet) -> tuple[EvidenceGapCandidate, ...]:
    """Return requirements with no registered evidence records.

    Record presence is intentionally not emitted as a positive assessment.
    """

    candidates: list[EvidenceGapCandidate] = []
    for requirement in evidence.requirements:
        if evidence.records_for(requirement.requirement_id):
            continue
        status = (
            EvidenceGapStatus.MANDATORY_NO_RECORD
            if requirement.mandatory
            else EvidenceGapStatus.OPTIONAL_NO_RECORD
        )
        candidates.append(
            EvidenceGapCandidate(
                requirement_id=requirement.requirement_id,
                control_id=requirement.control_id,
                status=status,
                reason=(
                    "No registered evidence record was found for the reviewed "
                    f"{'mandatory' if requirement.mandatory else 'optional'} requirement."
                ),
            )
        )
    return tuple(candidates)


T = TypeVar("T")


def _unique_index(
    items: Iterable[T],
    key_fn: Callable[[T], str],
    label: str,
) -> dict[str, T]:
    result: dict[str, T] = {}
    for item in items:
        key = key_fn(item)
        if key in result:
            raise ValueError(f"duplicate {label}: {key}")
        result[key] = item
    return result


def propagate_regulatory_change(
    change: RegulatoryChange,
    obligations: Iterable[Obligation],
    mappings: Iterable[ObligationControlMapping],
    controls: Iterable[Control],
    evidence: EvidenceSet,
) -> tuple[RegulatoryImpactCandidate, ...]:
    """Propagate one reviewed change through reviewed workflow relationships.

    Propagation means only that downstream organisation-owned artefacts should be
    reviewed because an upstream legal source changed. It never converts a
    change into a compliance verdict.
    """

    obligation_items = tuple(obligations)
    mapping_items = tuple(mappings)
    control_items = tuple(controls)

    obligation_by_id = _unique_index(
        obligation_items, lambda item: item.obligation_id, "obligation_id"
    )
    control_by_id = _unique_index(
        control_items, lambda item: item.control_id, "control_id"
    )

    mappings_by_obligation: dict[str, list[ObligationControlMapping]] = {}
    for mapping in mapping_items:
        if mapping.obligation_id not in obligation_by_id:
            raise ValueError(
                f"mapping references unknown obligation {mapping.obligation_id}"
            )
        if mapping.control_id not in control_by_id:
            raise ValueError(f"mapping references unknown control {mapping.control_id}")
        control = control_by_id[mapping.control_id]
        if control.obligation_id != mapping.obligation_id:
            raise ValueError(
                f"control {mapping.control_id} obligation does not match mapping"
            )
        mappings_by_obligation.setdefault(mapping.obligation_id, []).append(mapping)

    requirements_by_control: dict[str, list[str]] = {}
    for requirement in evidence.requirements:
        if requirement.control_id not in control_by_id:
            raise ValueError(
                f"evidence requirement {requirement.requirement_id} references "
                f"unknown control {requirement.control_id}"
            )
        requirements_by_control.setdefault(requirement.control_id, []).append(
            requirement.requirement_id
        )

    obligation_impacts = link_change_to_obligations(change, obligation_items)
    results: list[RegulatoryImpactCandidate] = []

    for obligation_impact in obligation_impacts:
        reviewed_mappings = mappings_by_obligation.get(
            obligation_impact.obligation_id, []
        )

        if not reviewed_mappings:
            results.append(
                RegulatoryImpactCandidate(
                    change_id=obligation_impact.change_id,
                    obligation_id=obligation_impact.obligation_id,
                    control_id=None,
                    requirement_ids=(),
                    upstream_link_status=obligation_impact.status,
                    status=RegulatoryImpactStatus.REVIEW_REQUIRED,
                    reason=(
                        "The regulatory change is linked to an obligation, but no "
                        "reviewed obligation-to-control mapping is available."
                    ),
                )
            )
            continue

        for mapping in sorted(reviewed_mappings, key=lambda item: item.control_id):
            requirement_ids = tuple(
                sorted(requirements_by_control.get(mapping.control_id, []))
            )
            results.append(
                RegulatoryImpactCandidate(
                    change_id=obligation_impact.change_id,
                    obligation_id=obligation_impact.obligation_id,
                    control_id=mapping.control_id,
                    requirement_ids=requirement_ids,
                    upstream_link_status=obligation_impact.status,
                    status=RegulatoryImpactStatus.REVIEW_REQUIRED,
                    reason=(
                        "An upstream reviewed regulatory change is linked to this "
                        "obligation; the reviewed control mapping and associated "
                        "evidence requirements should be re-examined."
                    ),
                )
            )

    return tuple(results)
