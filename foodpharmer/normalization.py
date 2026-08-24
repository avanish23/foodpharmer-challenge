"""Stage 2: raw ``ExtractedClaim`` -> :class:`NormalizedClaim`.

For each visible claim the provider classifies it into a :class:`ClaimType` and
fills the matching payload. All arithmetic and evidence lookups happen later in
deterministic Python code — the LLM is only responsible for language/vision
reasoning.
"""

from __future__ import annotations

from .models import NormalizedClaim, PackageExtraction
from .providers.base import LLMProvider


def normalize_claims(
    extraction: PackageExtraction, provider: LLMProvider
) -> list[NormalizedClaim]:
    """Normalize every visible claim in the extraction."""

    return [
        provider.normalize_claim(claim.claim, extraction) for claim in extraction.claims
    ]
