"""Resolver for :attr:`ClaimType.COMPARATIVE`.

The central invariant of this resolver: a vague baseline never yields
CONTRADICTED. "50% less oil than other chips" without an identified comparator
is UNSUBSTANTIATED — we simply cannot check it.

When both the product value and comparator data are available and the baseline
is specified, the resolver performs deterministic arithmetic (percentage
reduction or ratio) and reports SUBSTANTIATED / CONTRADICTED with a full
:class:`Computation` trace.
"""

from __future__ import annotations

from ..models import (
    ComparativePayload,
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
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
    assert isinstance(payload, ComparativePayload)

    # Rule #1 — unspecified baseline can never be substantiated OR contradicted.
    if not payload.baseline_specified:
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"The claim references '{payload.baseline_description}' but does not name a "
                "specific comparator product, published category average, or methodology. "
                "Without a defined baseline the claim cannot be verified or refuted."
            ),
            None,
        )

    value_entry = find(evidence, RequirementType.NUTRIENT_VALUE)
    comparator_entry = find(evidence, RequirementType.COMPARATOR_DATA)

    if not available(comparator_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"The baseline '{payload.baseline_description}' is specified, but no "
                f"{payload.metric} data for that comparator is available in this prototype."
            ),
            None,
        )
    if not available(value_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"Comparator data is available, but the product's own {payload.metric} value "
                "could not be located on the label."
            ),
            None,
        )

    assert value_entry is not None and comparator_entry is not None
    product_value: float | None = (value_entry.data or {}).get("value")
    comparator_value: float | None = (comparator_entry.data or {}).get("value")
    if product_value is None or comparator_value is None or comparator_value == 0:
        return (
            Verdict.UNSUBSTANTIATED,
            "Numeric values for both product and comparator are required to compute a comparison.",
            None,
        )

    if payload.magnitude_unit == "percent":
        return _percent_verdict(payload, product_value, comparator_value)
    if payload.magnitude_unit == "multiplier":
        return _multiplier_verdict(payload, product_value, comparator_value)
    return _absolute_verdict(payload, product_value, comparator_value)


def _percent_verdict(
    payload: ComparativePayload, product_value: float, comparator_value: float
) -> tuple[Verdict, str, Computation]:
    if payload.direction == "less":
        actual = (comparator_value - product_value) / comparator_value * 100
        passed = actual >= payload.magnitude
    else:  # "more"
        actual = (product_value - comparator_value) / comparator_value * 100
        passed = actual >= payload.magnitude
    computation = Computation(
        operation=f"percentage_{payload.direction}",
        inputs={
            "product_value": product_value,
            "comparator_value": comparator_value,
            "claimed_magnitude_pct": payload.magnitude,
        },
        result=round(actual, 3),
        unit="%",
        passed=passed,
    )
    if passed:
        return (
            Verdict.SUBSTANTIATED,
            (
                f"Product {payload.metric} of {product_value} vs comparator {comparator_value} "
                f"is {actual:.1f}% {payload.direction}, meeting the claimed {payload.magnitude}%."
            ),
            computation,
        )
    return (
        Verdict.CONTRADICTED,
        (
            f"Product {payload.metric} of {product_value} vs comparator {comparator_value} "
            f"is {actual:.1f}% {payload.direction}, short of the claimed {payload.magnitude}%."
        ),
        computation,
    )


def _multiplier_verdict(
    payload: ComparativePayload, product_value: float, comparator_value: float
) -> tuple[Verdict, str, Computation]:
    if payload.direction == "more":
        actual = product_value / comparator_value
    else:
        actual = comparator_value / product_value if product_value else 0.0
    passed = actual >= payload.magnitude
    computation = Computation(
        operation=f"multiplier_{payload.direction}",
        inputs={
            "product_value": product_value,
            "comparator_value": comparator_value,
            "claimed_multiplier": payload.magnitude,
        },
        result=round(actual, 3),
        unit="x",
        passed=passed,
    )
    verdict = Verdict.SUBSTANTIATED if passed else Verdict.CONTRADICTED
    reason = (
        f"Ratio of {payload.metric} between product ({product_value}) and comparator "
        f"({comparator_value}) is {actual:.2f}x versus the claimed {payload.magnitude}x."
    )
    return verdict, reason, computation


def _absolute_verdict(
    payload: ComparativePayload, product_value: float, comparator_value: float
) -> tuple[Verdict, str, Computation]:
    delta = product_value - comparator_value
    if payload.direction == "less":
        passed = -delta >= payload.magnitude
    else:
        passed = delta >= payload.magnitude
    computation = Computation(
        operation=f"absolute_{payload.direction}",
        inputs={
            "product_value": product_value,
            "comparator_value": comparator_value,
            "claimed_delta": payload.magnitude,
        },
        result=round(delta, 3),
        unit=None,
        passed=passed,
    )
    verdict = Verdict.SUBSTANTIATED if passed else Verdict.CONTRADICTED
    reason = (
        f"Difference in {payload.metric} between product ({product_value}) and comparator "
        f"({comparator_value}) is {delta:.2f} versus the claimed {payload.magnitude}."
    )
    return verdict, reason, computation
