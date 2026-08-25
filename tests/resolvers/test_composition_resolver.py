"""Composition resolver — presence + optional percentage disclosure."""

import unittest

from foodpharmer.models import (
    CompositionPayload,
    NormalizedClaim,
    RequirementType,
    Verdict,
)
from foodpharmer.resolvers.composition import resolve

from ._synth import empty_extraction, evidence


def _claim(component="whole wheat", claimed_percentage=100.0):
    payload = CompositionPayload(
        component=component,
        claimed_percentage=claimed_percentage,
        percentage_qualifier="100%" if claimed_percentage else "contains",
        disclosed_on_label=False,
    )
    return NormalizedClaim(
        claim_text=f"{claimed_percentage or ''}% {component}",
        claim_type=payload.claim_type,
        payload=payload,
    )


class CompositionResolverTests(unittest.TestCase):
    def test_ingredient_absent_from_complete_list_contradicted(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Refined wheat flour", "Sugar"], "complete": True},
            ),
            evidence(RequirementType.DECLARED_PERCENTAGE, available=False),
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.CONTRADICTED)

    def test_ingredient_present_but_no_disclosure_is_unsubstantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Whole wheat flour", "Bran"], "complete": True},
            ),
            evidence(RequirementType.DECLARED_PERCENTAGE, available=False),
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)

    def test_ingredient_present_with_matching_disclosure_substantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Whole wheat flour (100%)"], "complete": True},
            ),
            evidence(
                RequirementType.DECLARED_PERCENTAGE,
                available=True,
                data={"percentage": 100.0},
            ),
        ]
        verdict, _, computation = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.SUBSTANTIATED)
        self.assertTrue(computation.passed)

    def test_incomplete_list_is_unsubstantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Whole wheat flour"], "complete": False},
            ),
            evidence(RequirementType.DECLARED_PERCENTAGE, available=False),
        ]
        verdict, _, _ = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)

    def test_non_quantitative_presence_is_substantiated(self):
        evi = [
            evidence(
                RequirementType.INGREDIENT_LIST,
                available=True,
                data={"ingredients": ["Oats", "Sugar"], "complete": True},
            )
        ]
        verdict, _, _ = resolve(
            _claim(component="oats", claimed_percentage=None), evi, empty_extraction()
        )
        self.assertIs(verdict, Verdict.SUBSTANTIATED)


if __name__ == "__main__":
    unittest.main()
