"""Resolver for :attr:`ClaimType.SUPERLATIVE` (e.g. "India's #1 chips")."""

from __future__ import annotations

from ..models import (
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    RequirementType,
    SuperlativePayload,
    Verdict,
)
from ._helpers import available, find


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, SuperlativePayload)

    entry = find(evidence, RequirementType.MARKET_RANKING)
    if not available(entry):
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"'{payload.claim_phrase}' requires an authoritative market ranking, "
                "which is not available in this prototype."
            ),
            None,
        )
    # Real ranking logic would go here.
    return (
        Verdict.UNSUBSTANTIATED,
        "Market-ranking source returned data but no ranking check is implemented yet.",
        None,
    )
