"""Resolver for :attr:`ClaimType.ABSENCE` (e.g. "no added sugar", "0% maida")."""

from __future__ import annotations

import re

from ..models import (
    AbsencePayload,
    Computation,
    GatheredEvidence,
    NormalizedClaim,
    PackageExtraction,
    RequirementType,
    Verdict,
)
from ._helpers import available, find


_WORD_RE = re.compile(r"[a-z0-9]+")

# Common aliases — a "no maida" claim is contradicted by "refined wheat flour".
_ALIASES: dict[str, tuple[str, ...]] = {
    "maida": ("maida", "refined wheat flour"),
    "added sugar": ("added sugar", "sugar", "sucrose", "glucose syrup"),
    "trans fat": ("trans fat", "partially hydrogenated"),
}


def resolve(
    claim: NormalizedClaim,
    evidence: list[GatheredEvidence],
    extraction: PackageExtraction,
) -> tuple[Verdict, str, Computation | None]:
    payload = claim.payload
    assert isinstance(payload, AbsencePayload)

    ingredient_entry = find(evidence, RequirementType.INGREDIENT_LIST)
    if not available(ingredient_entry):
        return (
            Verdict.UNSUBSTANTIATED,
            "No ingredient list was extracted, so the absence claim cannot be checked.",
            None,
        )
    assert ingredient_entry is not None
    data = ingredient_entry.data or {}
    ingredients: list[str] = data.get("ingredients", [])
    complete = bool(data.get("complete"))

    if not complete:
        return (
            Verdict.UNSUBSTANTIATED,
            "The visible ingredient list is incomplete; presence of the ingredient cannot be ruled out.",
            None,
        )

    aliases = _ALIASES.get(payload.ingredient.lower(), (payload.ingredient.lower(),))
    matches = [ing for ing in ingredients if _contains_any(ing, aliases)]
    if matches:
        return (
            Verdict.CONTRADICTED,
            (
                f"'{payload.ingredient}' (or alias) is listed as an ingredient — {matches!r} — "
                "contradicting the absence claim."
            ),
            None,
        )
    return (
        Verdict.SUBSTANTIATED,
        (
            f"'{payload.ingredient}' does not appear in the complete visible ingredient list."
        ),
        None,
    )


def _contains_any(ingredient: str, aliases: tuple[str, ...]) -> bool:
    tokens = set(_WORD_RE.findall(ingredient.lower()))
    for alias in aliases:
        alias_tokens = set(_WORD_RE.findall(alias.lower()))
        if alias_tokens and alias_tokens.issubset(tokens):
            return True
    return False
