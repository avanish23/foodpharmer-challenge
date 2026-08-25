"""FSSAI evidence source — wraps the local PDF retriever.

Returns the retrieved chunks verbatim in ``data["evidence"]`` so downstream
resolvers can cite them. The FSSAI source does not parse numeric thresholds
from the PDFs — the resolver decides how to interpret the retrieved text. In
this prototype the resolver treats "any retrieval hit" as evidence that
motivated the qualifier's presence in the compendium, and (for canonical
qualifiers) uses hard-coded thresholds documented in the resolver.
"""

from __future__ import annotations

from ..models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
    RequirementType,
)
from ..retrieval import FssaiRuleRetriever


class FssaiRegulationSource:
    """Evidence source backed by ``LocalFssaiRetriever``."""

    source_id = "fssai"

    def __init__(self, retriever: FssaiRuleRetriever) -> None:
        self._retriever = retriever

    def can_fulfill(self, requirement: EvidenceRequirement) -> bool:
        return requirement.requirement_type is RequirementType.FSSAI_THRESHOLD

    def fulfill(
        self,
        requirement: EvidenceRequirement,
        extraction: PackageExtraction,
    ) -> GatheredEvidence:
        nutrition_context = "\n".join(
            f"{fact.nutrient}: {fact.value}" for fact in extraction.nutrition_facts
        )
        hits = self._retriever.retrieve(requirement.description, nutrition_context, limit=3)
        if not hits:
            return GatheredEvidence(
                requirement=requirement,
                status=EvidenceStatus.UNAVAILABLE,
                data=None,
                source=self.source_id,
                note="No FSSAI rule was retrieved for this claim.",
            )
        return GatheredEvidence(
            requirement=requirement,
            status=EvidenceStatus.AVAILABLE,
            data={"evidence": [hit.model_dump(mode="json") for hit in hits]},
            source=self.source_id,
        )
