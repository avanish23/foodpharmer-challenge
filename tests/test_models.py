"""Round-trip tests for the core Pydantic models."""

import unittest

from foodpharmer.models import (
    ClaimType,
    ComparativePayload,
    CompositionPayload,
    NormalizedClaim,
    NutrientContentPayload,
    SubjectiveMarketingPayload,
    Verdict,
)


class NormalizedClaimTests(unittest.TestCase):
    def test_discriminated_union_dispatches_by_claim_type(self):
        raw = {
            "claim_text": "High Fibre",
            "claim_type": "NUTRIENT_CONTENT",
            "payload": {
                "claim_type": "NUTRIENT_CONTENT",
                "nutrient": "dietary fibre",
                "qualifier": "high",
                "declared_value": 8.2,
                "declared_unit": "g",
                "declared_per": "per 100 g",
            },
        }
        claim = NormalizedClaim.model_validate(raw)
        self.assertIs(claim.claim_type, ClaimType.NUTRIENT_CONTENT)
        self.assertIsInstance(claim.payload, NutrientContentPayload)
        self.assertEqual(claim.payload.declared_value, 8.2)

    def test_comparative_baseline_specified_is_required(self):
        payload = ComparativePayload(
            metric="oil",
            magnitude=50.0,
            magnitude_unit="percent",
            direction="less",
            baseline_description="other chips",
            baseline_specified=False,
        )
        self.assertFalse(payload.baseline_specified)
        self.assertEqual(payload.claim_type, ClaimType.COMPARATIVE)

    def test_composition_payload_disclosed_flag(self):
        payload = CompositionPayload(
            component="whole wheat",
            claimed_percentage=100.0,
            percentage_qualifier="100%",
            disclosed_on_label=False,
        )
        self.assertFalse(payload.disclosed_on_label)

    def test_subjective_marketing_payload_round_trip(self):
        payload = SubjectiveMarketingPayload(
            phrase="guilt-free",
            reason_non_falsifiable="Emotional descriptor, no measurable property.",
        )
        again = SubjectiveMarketingPayload.model_validate(payload.model_dump())
        self.assertEqual(payload, again)

    def test_verdict_enum_values(self):
        self.assertEqual(
            {v.value for v in Verdict},
            {"SUBSTANTIATED", "CONTRADICTED", "UNSUBSTANTIATED", "NON_FALSIFIABLE"},
        )


if __name__ == "__main__":
    unittest.main()
