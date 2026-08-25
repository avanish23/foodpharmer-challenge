"""Resolver for :attr:`ClaimType.COMPOSITION`.

A "100% X" claim needs both the ingredient present and the actual percentage
disclosed on the label. The most interesting case is "Made with 100% whole
wheat" on a package whose ingredient list starts with "whole wheat" but does
not disclose a percentage — this must land as UNSUBSTANTIATED, not
SUBSTANTIATED.
"""

from __future__ import annotations

import re

from ..models import (
    CompositionPayload,
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    RequirementType,
    Verdict,
)
from ._helpers import available, find


_WORD_RE = re.compile(r"[a-z0-9]+")


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, CompositionPayload)

    ingredient_entry = find(evidence, RequirementType.INGREDIENT_LIST)
    percentage_entry = find(evidence, RequirementType.DECLARED_PERCENTAGE)

    if not available(ingredient_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            "The ingredient list is not available, so composition cannot be checked.",
            None,
        )

    assert ingredient_entry is not None
    data = ingredient_entry.data or {}
    ingredients: list[str] = data.get("ingredients", [])
    complete: bool = bool(data.get("complete"))
    component_present = _contains_component(ingredients, payload.component)

    if not complete:
        return (
            Verdict.UNSUBSTANTIATED,
            "The visible ingredient list is not complete; composition cannot be verified.",
            None,
        )

    if not component_present:
        return (
            Verdict.CONTRADICTED,
            (
                f"'{payload.component}' does not appear in the complete visible ingredient "
                "list, contradicting the composition claim."
            ),
            None,
        )

    # Component is present and list is complete. If the claim is quantitative
    # (e.g. "100% whole wheat") we need a disclosed percentage.
    if payload.claimed_percentage is not None:
        if not available(percentage_entry):
            return (
                Verdict.UNSUBSTANTIATED,
                (
                    f"'{payload.component}' is present in the ingredient list, but the "
                    f"actual {payload.component} percentage is not disclosed on the label, "
                    f"so the claimed {payload.claimed_percentage}% cannot be verified."
                ),
                None,
            )
        assert percentage_entry is not None
        disclosed = (percentage_entry.data or {}).get("percentage")
        passed = disclosed is not None and float(disclosed) >= payload.claimed_percentage
        computation = Computation(
            operation="composition_percentage_check",
            inputs={
                "component": payload.component,
                "claimed_percentage": payload.claimed_percentage,
                "disclosed_percentage": disclosed,
            },
            result=disclosed,
            unit="%",
            passed=passed,
        )
        if passed:
            return (
                Verdict.SUBSTANTIATED,
                (
                    f"Label discloses {disclosed}% {payload.component}, meeting the claimed "
                    f"{payload.claimed_percentage}%."
                ),
                computation,
            )
        return (
            Verdict.CONTRADICTED,
            (
                f"Label discloses {disclosed}% {payload.component}, less than the claimed "
                f"{payload.claimed_percentage}%."
            ),
            computation,
        )

    # Non-quantitative composition ("contains X"): presence alone suffices.
    return (
        Verdict.SUBSTANTIATED,
        f"'{payload.component}' is present in the complete ingredient list.",
        None,
    )


def _contains_component(ingredients: list[str], component: str) -> bool:
    tokens = set(_WORD_RE.findall(component.lower()))
    if not tokens:
        return False
    for ingredient in ingredients:
        ingredient_tokens = set(_WORD_RE.findall(ingredient.lower()))
        if tokens.issubset(ingredient_tokens):
            return True
    return False
