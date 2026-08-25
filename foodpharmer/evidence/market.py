"""Stub market/ranking source.

Same shape as :class:`ComparatorProductSource` — Protocol wired in, always
UNAVAILABLE. Replace with an authoritative rankings dataset when available.
"""

from __future__ import annotations

from ..models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
    RequirementType,
)


class MarketDataSource:
    """Placeholder — always UNAVAILABLE."""

    source_id = "market_data"

    def can_fulfill(self, requirement: EvidenceRequirement) -> bool:
        return requirement.requirement_type is RequirementType.MARKET_RANKING

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
            note="Market/ranking dataset is not wired up in this prototype.",
        )
