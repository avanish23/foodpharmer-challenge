"""Absence resolver — hinges on ingredient_list_complete."""

import unittest

from foodpharmer.models import (
    AbsencePayload,
    NormalizedClaim,
    RequirementType,
    Verdict,
)
from foodpharmer.resolvers.absence import resolve

from ._synth import empty_extraction, evidence


def _claim(ingredient="added sugar", claim_form="No added sugar", zero_percent=False):
    payload = AbsencePayload(
        ingredient=ingredient, claim_form=claim_form, zero_percent=zero_percent
    )
    return NormalizedClaim(
        claim_text=claim_form, claim_type=payload.claim_type, payload=payload
    )


class AbsenceResolverTests(unittest.TestCase):
    def test_absent_from_complete_list_is_substantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Whole wheat flour", "Salt"], "complete": True},
            )
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.SUBSTANTIATED)

    def test_present_in_list_is_contradicted(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Refined wheat flour", "Added sugar", "Salt"], "complete": True},
            )
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.CONTRADICTED)

    def test_incomplete_list_is_unsubstantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Whole wheat flour"], "complete": False},
            )
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)

    def test_alias_is_matched(self):
        # "No maida" is contradicted by "Refined wheat flour" via alias.
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Refined wheat flour", "Sugar"], "complete": True},
            )
        ]
        verdict, _, _ = resolve(
            _claim(ingredient="maida", claim_form="No maida"), evi, empty_extraction()
        )
        self.assertIs(verdict, Verdict.CONTRADICTED)


if __name__ == "__main__":
    unittest.main()
