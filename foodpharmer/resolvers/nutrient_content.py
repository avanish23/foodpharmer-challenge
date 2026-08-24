"""Resolver for :attr:`ClaimType.NUTRIENT_CONTENT`.

Rule of thumb:

* Both NUTRIENT_VALUE and FSSAI_THRESHOLD available → threshold arithmetic in
  Python → SUBSTANTIATED / CONTRADICTED.
* Either UNAVAILABLE → UNSUBSTANTIATED (never CONTRADICTED).

The FSSAI PDF text is not machine-parsed for numeric thresholds in this
prototype. For the canonical qualifier keywords listed in ``_QUALIFIER_THRESHOLDS``
we apply the well-known FSSAI Compendium values (per 100 g of solid food) when
the retriever confirmed there is a rule to cite. If the qualifier is not in
the built-in table the resolver reports UNSUBSTANTIATED and cites the FSSAI
hits — this is deliberate: better to say "we cannot decide" than to invent a
threshold.
"""

from __future__ import annotations

from ..models import (
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    NutrientContentPayload,
    PackageExtraction,
    RequirementType,
    Verdict,
)
from ._helpers import available, find


# Canonical FSSAI (per 100 g of solid food) thresholds. Values match the
# Compendium of Advertising Claims Regulations. The mapping is intentionally
# small — extend it by adding rows here, not by asking the LLM.
_QUALIFIER_THRESHOLDS: dict[tuple[str, str], tuple[str, float, str]] = {
    # (qualifier keyword, nutrient keyword) -> (operator, value, unit)
    ("high", "fibre"): (">=", 6.0, "g"),
    ("high", "fiber"): (">=", 6.0, "g"),
    ("source", "fibre"): (">=", 3.0, "g"),
    ("source", "fiber"): (">=", 3.0, "g"),
    ("high", "protein"): (">=", 10.0, "g"),
    ("source", "protein"): (">=", 5.0, "g"),
    ("rich", "protein"): (">=", 10.0, "g"),
    ("low", "fat"): ("<=", 3.0, "g"),
    ("low", "sugar"): ("<=", 5.0, "g"),
    ("low", "sodium"): ("<=", 0.12, "g"),
}


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, NutrientContentPayload)

    value_entry = find(evidence, RequirementType.NUTRIENT_VALUE)
    threshold_entry = find(evidence, RequirementType.FSSAI_THRESHOLD)

    if not available(value_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"The declared value of {payload.nutrient} is not visible on the "
                "label, so the '{qualifier}' claim cannot be verified."
            ).format(qualifier=payload.qualifier),
            None,
        )
    if not available(threshold_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"No FSSAI criterion for '{payload.qualifier} {payload.nutrient}' was "
                "retrieved from the local corpus, so the qualifying threshold is unknown."
            ),
            None,
        )

    threshold = _lookup_threshold(payload.qualifier, payload.nutrient)
    assert value_entry is not None
    data = value_entry.data or {}
    declared_value: float | None = data.get("value")
    declared_unit: str | None = data.get("unit")

    if threshold is None:
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"FSSAI evidence was retrieved for '{payload.qualifier} {payload.nutrient}', "
                "but this prototype has no encoded threshold for that qualifier, so the "
                "arithmetic check cannot be performed deterministically."
            ),
            None,
        )
    if declared_value is None:
        return (
            Verdict.UNSUBSTANTIATED,
            (
                f"A {payload.nutrient} value was located on the label but could not be "
                "parsed to a numeric quantity for comparison."
            ),
            None,
        )

    operator, limit, unit = threshold
    passed = _compare(operator, declared_value, limit)
    computation = Computation(
        operation="nutrient_threshold_check",
        inputs={
            "nutrient": payload.nutrient,
            "qualifier": payload.qualifier,
            "declared_value": declared_value,
            "declared_unit": declared_unit,
            "threshold_operator": operator,
            "threshold_value": limit,
            "threshold_unit": unit,
        },
        result=declared_value,
        unit=declared_unit or unit,
        passed=passed,
    )
    if passed:
        return (
            Verdict.SUBSTANTIATED,
            (
                f"Declared {payload.nutrient} of {declared_value}{declared_unit or ''} meets "
                f"the FSSAI criterion of {operator} {limit} {unit} for a '{payload.qualifier}' claim."
            ),
            computation,
        )
    return (
        Verdict.CONTRADICTED,
        (
            f"Declared {payload.nutrient} of {declared_value}{declared_unit or ''} does not "
            f"satisfy the FSSAI criterion of {operator} {limit} {unit} for a "
            f"'{payload.qualifier}' claim."
        ),
        computation,
    )


def _lookup_threshold(qualifier: str, nutrient: str) -> tuple[str, float, str] | None:
    q = qualifier.strip().lower().split()[0] if qualifier.strip() else ""
    n = nutrient.strip().lower()
    for token in n.split():
        key = (q, token)
        if key in _QUALIFIER_THRESHOLDS:
            return _QUALIFIER_THRESHOLDS[key]
    return None


def _compare(operator: str, value: float, limit: float) -> bool:
    if operator == ">=":
        return value >= limit
    if operator == "<=":
        return value <= limit
    if operator == ">":
        return value > limit
    if operator == "<":
        return value < limit
    raise ValueError(f"Unsupported operator {operator!r}.")
