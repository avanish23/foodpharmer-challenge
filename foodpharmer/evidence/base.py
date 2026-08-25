"""Evidence-source Protocol and dispatcher.

An :class:`EvidenceSource` promises two things: whether it can answer a given
:class:`EvidenceRequirement`, and — if asked — what it found. Sources should
never fabricate: if the answer is unknown, return UNAVAILABLE with an optional
``note`` explaining why.
"""

from __future__ import annotations

from typing import Protocol

from ..models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
)


class EvidenceSource(Protocol):
    """One backend able to answer some subset of :class:`RequirementType`."""

    source_id: str

    def can_fulfill(self, requirement: EvidenceRequirement) -> bool: ...

    def fulfill(
        self,
        requirement: EvidenceRequirement,
        extraction: PackageExtraction,
    ) -> GatheredEvidence: ...


def gather_all(
    requirements: list[EvidenceRequirement],
    extraction: PackageExtraction,
    sources: list[EvidenceSource],
) -> list[GatheredEvidence]:
    """Ask each source to fulfill each requirement, in registration order.

    Every requirement produces exactly one :class:`GatheredEvidence` — if no
    registered source can even attempt it, we still record an UNAVAILABLE
    entry so the reasoning chain is complete in the JSON output.
    """

    gathered: list[GatheredEvidence] = []
    for requirement in requirements:
        for source in sources:
            if source.can_fulfill(requirement):
                gathered.append(source.fulfill(requirement, extraction))
                break
        else:
            gathered.append(
                GatheredEvidence(
                    requirement=requirement,
                    status=EvidenceStatus.UNAVAILABLE,
                    data=None,
                    source="none",
                    note="No registered evidence source can fulfill this requirement.",
                )
            )
    return gathered
