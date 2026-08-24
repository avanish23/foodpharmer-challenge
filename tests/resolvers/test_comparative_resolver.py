"""Comparative resolver — the case the whole exercise turns on."""

import unittest

from foodpharmer.models import (
    ComparativePayload,
    NormalizedClaim,
    RequirementType,
    Verdict,
)
from foodpharmer.resolvers.comparative import resolve

from ._synth import empty_extraction, evidence


def _claim(**overrides):
    fields = {
        "metric": "oil",
        "magnitude": 50.0,
        "magnitude_unit": "percent",
        "direction": "less",
        "baseline_description": "other chips",
        "baseline_specified": False,
    }
    fields.update(overrides)
    payload = ComparativePayload(**fields)
    return NormalizedClaim(claim_text="50% less oil", claim_type=payload.claim_type, payload=payload)


class ComparativeResolverTests(unittest.TestCase):
    def test_unspecified_baseline_is_unsubstantiated_not_contradicted(self):
        # Even with the product value available, a vague baseline blocks any
        # verdict beyond UNSUBSTANTIATED.
        claim = _claim(baseline_specified=False)
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=True, data={"value": 25.0, "unit": "g"}),
            evidence(RequirementType.COMPARATOR_DATA, available=False),
        ]
        verdict, reason, computation = resolve(claim, evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(computation)
        self.assertIn("baseline", reason.lower())

    def test_specified_baseline_but_comparator_unavailable_is_unsubstantiated(self):
        claim = _claim(baseline_description="Brand X regular chips", baseline_specified=True)
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=True, data={"value": 25.0, "unit": "g"}),
            evidence(RequirementType.COMPARATOR_DATA, available=False),
        ]
        verdict, _, computation = resolve(claim, evi, empty_extraction())
        self.assertIs(verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(computation)

    def test_fifty_percent_less_substantiated_with_arithmetic(self):
        claim = _claim(baseline_description="Brand X regular chips", baseline_specified=True)
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=True, data={"value": 25.0, "unit": "g"}),
            evidence(RequirementType.COMPARATOR_DATA, available=True, data={"value": 50.0, "unit": "g"}),
        ]
        verdict, _, computation = resolve(claim, evi, empty_extraction())
        self.assertIs(verdict, Verdict.SUBSTANTIATED)
        self.assertIsNotNone(computation)
        self.assertAlmostEqual(computation.result, 50.0, places=3)
        self.assertTrue(computation.passed)

    def test_fifty_percent_less_contradicted(self):
        claim = _claim(baseline_description="Brand X regular chips", baseline_specified=True)
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=True, data={"value": 35.0, "unit": "g"}),
            evidence(RequirementType.COMPARATOR_DATA, available=True, data={"value": 50.0, "unit": "g"}),
        ]
        verdict, _, computation = resolve(claim, evi, empty_extraction())
        self.assertIs(verdict, Verdict.CONTRADICTED)
        self.assertAlmostEqual(computation.result, 30.0, places=3)
        self.assertFalse(computation.passed)

    def test_two_times_more_multiplier_substantiated(self):
        payload = ComparativePayload(
            metric="protein",
            magnitude=2.0,
            magnitude_unit="multiplier",
            direction="more",
            baseline_description="Category average per Euromonitor 2024",
            baseline_specified=True,
        )
        claim = NormalizedClaim(claim_text="2x more protein", claim_type=payload.claim_type, payload=payload)
        evi = [
            evidence(RequirementType.NUTRIENT_VALUE, available=True, data={"value": 20.0, "unit": "g"}),
            evidence(RequirementType.COMPARATOR_DATA, available=True, data={"value": 9.0, "unit": "g"}),
        ]
        verdict, _, computation = resolve(claim, evi, empty_extraction())
        self.assertIs(verdict, Verdict.SUBSTANTIATED)
        self.assertAlmostEqual(computation.result, 20 / 9, places=3)
        self.assertTrue(computation.passed)


if __name__ == "__main__":
    unittest.main()
