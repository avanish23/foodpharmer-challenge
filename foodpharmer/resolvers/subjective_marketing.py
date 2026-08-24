"""Resolver for :attr:`ClaimType.SUBJECTIVE_MARKETING` (e.g. "guilt-free")."""

from __future__ import annotations

from ..models import (
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    SubjectiveMarketingPayload,
    Verdict,
)


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, SubjectiveMarketingPayload)
    return (
        Verdict.NON_FALSIFIABLE,
        (
            f"'{payload.phrase}' is subjective marketing language. "
            f"{payload.reason_non_falsifiable}"
        ).strip(),
        None,
    )
