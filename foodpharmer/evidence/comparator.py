"""Stub comparator-products source.

Returns UNAVAILABLE for every COMPARATOR_DATA request. Wired into the pipeline
today so the Protocol is exercised; replace ``fulfill`` with a real data loader
(a CSV/JSON of category averages, for example) when comparator data is
available.
"""

from __future__ import annotations

from ..models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
    RequirementType,
)


class ComparatorProductSource:
    """Placeholder — always UNAVAILABLE."""

    source_id = "comparator_products"

    def can_fulfill(self, requirement: EvidenceRequirement) -> bool:
        return requirement.requirement_type is RequirementType.COMPARATOR_DATA

    def fulfill(
        self,
        requirement: EvidenceRequirement,
        extraction: PackageExtraction,
    ) -> GatheredEvidence:
        return GatheredEvidence(
            requirement=requirement,
            status=EvidenceStatus.UNAVAILABLE,
            data=None,
            source=self.source_id,
            note="Comparator-product dataset is not wired up in this prototype.",
        )
