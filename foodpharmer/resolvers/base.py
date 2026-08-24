"""Dispatcher — routes each normalized claim to its resolver."""

from __future__ import annotations

from ..models import (
    ClaimType,
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    Verdict,
)
from . import (
    absence,
    comparative,
    composition,
    nutrient_content,
    quantitative,
    scientific,
    subjective_marketing,
    superlative,
)


_RESOLVERS = {
    ClaimType.NUTRIENT_CONTENT: nutrient_content.resolve,
    ClaimType.COMPARATIVE: comparative.resolve,
    ClaimType.COMPOSITION: composition.resolve,
    ClaimType.ABSENCE: absence.resolve,
    ClaimType.QUANTITATIVE: quantitative.resolve,
    ClaimType.SUPERLATIVE: superlative.resolve,
    ClaimType.SCIENTIFIC: scientific.resolve,
    ClaimType.SUBJECTIVE_MARKETING: subjective_marketing.resolve,
}


def resolve_claim(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    """Return the verdict, human reason, and computation trace for one claim."""

    try:
        resolver = _RESOLVERS[claim.claim_type]
    except KeyError as error:
        raise ValueError(f"No resolver registered for {claim.claim_type}.") from error
    return resolver(claim, evidence, extraction)
