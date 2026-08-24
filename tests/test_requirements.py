"""Requirement-derivation is deterministic and keyed on ClaimType."""

import unittest

from foodpharmer.models import (
    AbsencePayload,
    ClaimType,
    ComparativePayload,
    CompositionPayload,
    NormalizedClaim,
    NutrientContentPayload,
    RequirementType,
    SubjectiveMarketingPayload,
    SuperlativePayload,
)
from foodpharmer.requirements import derive_requirements


def _wrap(payload):
    return NormalizedClaim(
        claim_text="x", claim_type=payload.claim_type, payload=payload
    )


class RequirementTests(unittest.TestCase):
    def test_nutrient_content_requires_value_and_threshold(self):
        payload = NutrientContentPayload(nutrient="dietary fibre", qualifier="high")
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs],
            [RequirementType.NUTRIENT_VALUE, RequirementType.FSSAI_THRESHOLD],
        )

    def test_comparative_requires_value_and_comparator(self):
        payload = ComparativePayload(
            metric="oil",
            magnitude=50.0,
            magnitude_unit="percent",
            direction="less",
            baseline_description="other chips",
            baseline_specified=False,
        )
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs],
            [RequirementType.NUTRIENT_VALUE, RequirementType.COMPARATOR_DATA],
        )

    def test_composition_with_percentage_adds_declared_percentage(self):
        payload = CompositionPayload(
            component="whole wheat",
            claimed_percentage=100.0,
            percentage_qualifier="100%",
            disclosed_on_label=False,
        )
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs],
            [RequirementType.INGREDIENT_LIST, RequirementType.DECLARED_PERCENTAGE],
        )

    def test_composition_without_percentage_omits_declared_percentage(self):
        payload = CompositionPayload(
            component="oats",
            claimed_percentage=None,
            percentage_qualifier="contains",
            disclosed_on_label=False,
        )
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs], [RequirementType.INGREDIENT_LIST]
        )

    def test_absence_requires_ingredient_list(self):
        payload = AbsencePayload(
            ingredient="added sugar",
            claim_form="No added sugar",
            zero_percent=False,
        )
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs], [RequirementType.INGREDIENT_LIST]
        )

    def test_superlative_requires_market_ranking(self):
        payload = SuperlativePayload(claim_phrase="India's #1", domain="chips")
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(
            [r.requirement_type for r in reqs], [RequirementType.MARKET_RANKING]
        )

    def test_subjective_marketing_derives_no_requirements(self):
        payload = SubjectiveMarketingPayload(
            phrase="guilt-free", reason_non_falsifiable="subjective"
        )
        reqs = derive_requirements(_wrap(payload))
        self.assertEqual(reqs, [])


if __name__ == "__main__":
    unittest.main()
