"""Subjective marketing always yields NON_FALSIFIABLE."""

import unittest

from foodpharmer.models import (
    NormalizedClaim,
    SubjectiveMarketingPayload,
    Verdict,
)
from foodpharmer.resolvers.subjective_marketing import resolve

from ._synth import empty_extraction


class SubjectiveMarketingResolverTests(unittest.TestCase):
    def test_always_non_falsifiable(self):
        payload = SubjectiveMarketingPayload(
            phrase="guilt-free",
            reason_non_falsifiable="Emotional descriptor, not measurable.",
        )
        claim = NormalizedClaim(
            claim_text="guilt-free", claim_type=payload.claim_type, payload=payload
        )
        verdict, reason, computation = resolve(claim, [], empty_extraction())
        self.assertIs(verdict, Verdict.NON_FALSIFIABLE)
        self.assertIn("guilt-free", reason)
        self.assertIsNone(computation)


if __name__ == "__main__":
    unittest.main()
