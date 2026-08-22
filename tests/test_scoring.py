import unittest

from foodpharmer.scoring import marketing_gap_score


class MarketingGapScoreTests(unittest.TestCase):
    def test_returns_percentage_of_not_supported_assessable_claims(self):
        score = marketing_gap_score(
            ["SUPPORTED", "NOT_SUPPORTED", "INSUFFICIENT_INFORMATION", "NOT_SUPPORTED"]
        )

        self.assertAlmostEqual(score, 66.66666666666666)

    def test_insufficient_information_does_not_affect_score(self):
        self.assertEqual(marketing_gap_score(["SUPPORTED", "INSUFFICIENT_INFORMATION"]), 0.0)

    def test_returns_none_when_no_claim_is_assessable(self):
        self.assertIsNone(marketing_gap_score([]))
        self.assertIsNone(marketing_gap_score(["INSUFFICIENT_INFORMATION"]))


if __name__ == "__main__":
    unittest.main()
