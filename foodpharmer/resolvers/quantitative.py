"""Resolver for :attr:`ClaimType.QUANTITATIVE`.

A raw numeric assertion ("10g protein per serve") is SUBSTANTIATED when the
label declares a value at least as large as the claim, CONTRADICTED when the
declared value is smaller, and UNSUBSTANTIATED when no value is available.
"""

from __future__ import annotations

from ..models import (
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    QuantitativePayload,
    RequirementType,
    Verdict,
)
from ._helpers import available, find


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, QuantitativePayload)

    entry = find(evidence, RequirementType.NUTRIENT_VALUE)
    if not available(entry):
        return (
            Verdict.UNSUBSTANTIATED,
            f"No declared value for {payload.metric} was found on the label.",
            None,
        )
    assert entry is not None
    declared = (entry.data or {}).get("value")
    if declared is None:
        return (
            Verdict.UNSUBSTANTIATED,
            f"A {payload.metric} value was found but could not be parsed numerically.",
            None,
        )
    passed = float(declared) >= payload.value
    computation = Computation(
        operation="quantitative_check",
        inputs={"declared_value": declared, "claimed_value": payload.value, "unit": payload.unit},
        result=declared,
        unit=payload.unit,
        passed=passed,
    )
    verdict = Verdict.SUBSTANTIATED if passed else Verdict.CONTRADICTED
    reason = (
        f"Declared {payload.metric} of {declared} {payload.unit or ''} "
        f"{'meets' if passed else 'falls short of'} the claimed {payload.value} {payload.unit}."
    )
    return verdict, reason, computation
