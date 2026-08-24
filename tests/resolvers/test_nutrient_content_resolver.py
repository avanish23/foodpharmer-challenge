"""Nutrient-content resolver — threshold arithmetic against FSSAI evidence."""

import unittest

from foodpharmer.models import (
    NormalizedClaim,
    NutrientContentPayload,
    RequirementType,
    Verdict,
)
from foodpharmer.resolvers.nutrient_content import resolve

from ._synth import empty_extraction, evidence


def _claim(nutrient="dietary fibre", qualifier="high"):
    payload = NutrientContentPayload(nutrient=nutrient, qualifier=qualifier)
    return NormalizedClaim(
        claim_text=f"{qualifier} {nutrient}",
        claim_type=payload.claim_type,
        payload=payload,
    )


class NutrientContentResolverTests(unittest.TestCase):
    def test_value_meets_threshold_substantiated(self):
        evi = [
            evidence(
                RequirementType.NUTRIENT_VALUE,
                available=True,
                data={"nutrient": "Dietary Fibre", "value": 8.2, "unit": "g"},
            ),
            evidence(
                RequirementType.FSSAI_THRESHOLD,
                available=True,
                data={"evidence": [{"text": "High fibre >= 6g per 100g"}]},
            ),
        ]
        verdict, _, computation = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.SUBSTANTIATED)
        self.assertIsNotNone(computation)
        self.assertTrue(computation.passed)

    def test_value_below_threshold_contradicted(self):
        evi = [
            evidence(
                RequirementType.NUTRIENT_VALUE,
                available=True,
                data={"nutrient": "Dietary Fibre", "value": 3.0, "unit": "g"},
            ),
            evidence(RequirementType.FSSAI_THRESHOLD, available=True, data={"evidence": []}),
        ]
        verdict, _, computation = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.CONTRADICTED)
        self.assertFalse(computation.passed)

    def test_threshold_unavailable_is_unsubstantiated(self):
        evi = [
            evidence(
                RequirementType.NUTRIENT_VALUE,
                available=True,
                data={"nutrient": "Dietary Fibre", "value": 8.2, "unit": "g"},
            ),
            evidence(RequirementType.FSSAI_THRESHOLD, available=False),
        ]
        verdict, _, computation = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(computation)

    def test_nutrient_value_unavailable_is_unsubstantiated(self):
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=False),
            evidence(RequirementType.FSSAI_THRESHOLD, available=True, data={"evidence": []}),
        ]
        verdict, _, computation = resolve(_claim(), evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(computation)

    def test_unmapped_qualifier_is_unsubstantiated(self):
        evi = [
            evidence(
                RequirementType.NUTRIENT_VALUE,
                available=True,
                data={"nutrient": "Iron", "value": 5.0, "unit": "mg"},
            ),
            evidence(RequirementType.FSSAI_THRESHOLD, available=True, data={"evidence": []}),
        ]
        verdict, _, computation = resolve(
            _claim(nutrient="iron", qualifier="excellent"), evi, empty_extraction()
        )
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(computation)


if __name__ == "__main__":
    unittest.main()
