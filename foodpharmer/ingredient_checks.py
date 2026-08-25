"""Deterministic ingredient-list checks.

This is a small factual helper — matches ``0% X`` style claims against the
visible ingredient list. It does not decide claim verdicts; the ABSENCE and
COMPOSITION resolvers consume its output.

Ported verbatim from ``feature/v2-fssai-retrieval``.
"""

import re

from .models import IngredientListCheck, IngredientListCheckStatus


_ZERO_PERCENT_CLAIM = re.compile(r"^\s*0\s*%\s*(?P<ingredient>.+?)\s*$", re.IGNORECASE)
_ALIASES = {
    "maida": ("maida", "refined wheat flour"),
}


def check_ingredient_list(
    claim: str,
    ingredients: list[str],
    ingredient_list_complete: bool,
) -> IngredientListCheck | None:
    """Check a visible ``0% ingredient`` claim against the visible ingredient list.

    Reports label consistency only. Returns INSUFFICIENT_INFORMATION when the
    ingredient list is not visibly complete.
    """

    match = _ZERO_PERCENT_CLAIM.match(claim)
    if not match:
        return None

    claim_term = _normalize(match.group("ingredient"))
    terms = list(_ALIASES.get(claim_term, (claim_term,)))
    if not ingredient_list_complete:
        return IngredientListCheck(
            status=IngredientListCheckStatus.INSUFFICIENT_INFORMATION,
            terms_checked=terms,
            evidence=ingredients,
        )

    matching_entries = [
        ingredient
        for ingredient in ingredients
        if any(_contains_term(ingredient, term) for term in terms)
    ]
    if matching_entries:
        return IngredientListCheck(
            status=IngredientListCheckStatus.LISTED,
            terms_checked=terms,
            evidence=matching_entries,
        )
    return IngredientListCheck(
        status=IngredientListCheckStatus.NOT_LISTED,
        terms_checked=terms,
        evidence=ingredients,
    )


def _contains_term(ingredient: str, term: str) -> bool:
    normalized_ingredient = f" {_normalize(ingredient)} "
    return f" {term} " in normalized_ingredient


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))
