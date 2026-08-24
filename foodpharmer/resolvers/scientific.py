"""Resolver for :attr:`ClaimType.SCIENTIFIC` (e.g. "clinically proven").

Without a peer-review evidence source this prototype cannot verify scientific
claims; the resolver always reports UNSUBSTANTIATED. It never labels such a
claim CONTRADICTED — that would require actual counter-evidence.
"""

from __future__ import annotations

from ..models import (
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    ScientificPayload,
    Verdict,
)


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, ScientificPayload)
    return (
        Verdict.UNSUBSTANTIATED,
        (
            f"'{payload.claim_phrase}' requires peer-reviewed evidence, and no scientific "
            "evidence source is wired into this prototype."
        ),
        None,
    )
