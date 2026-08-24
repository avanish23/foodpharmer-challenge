"""End-to-end pipeline over the five canonical fixture cases.

Uses :class:`FixtureProvider` so no API key is required. FSSAI evidence comes
from a small in-memory stub retriever so the test does not depend on the real
Compendium PDF being parseable.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from foodpharmer.evidence import (
    ComparatorProductSource,
    FssaiRegulationSource,
    MarketDataSource,
    PackagingSource,
)
from foodpharmer.models import RuleEvidence, Verdict
from foodpharmer.pipeline import analyze
from foodpharmer.providers.fixture_provider import FixtureProvider


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _StubRetriever:
    """Returns one canned RuleEvidence for any retrieval — enough for the
    fixture cases where the FSSAI source only needs to signal AVAILABLE."""

    def retrieve(self, claim: str, context: str, limit: int = 3) -> list[RuleEvidence]:
        return [
            RuleEvidence(
                document="FSSAI Advertising Claims Compendium",
                source="stub",
                page_number=1,
                section="SCHEDULE I",
                text=(
                    "High fibre: dietary fibre content of the food must not be less "
                    "than 6 g per 100 g of solid food."
                ),
            )
        ]


def _sources():
    return [
        PackagingSource(),
        FssaiRegulationSource(_StubRetriever()),
        ComparatorProductSource(),
        MarketDataSource(),
    ]


CASES = [
    ("high_fibre", "High Fibre", Verdict.SUBSTANTIATED),
    ("less_oil", "50% less oil than other chips", Verdict.UNSUBSTANTIATED),
    ("more_protein", "2x more protein", Verdict.UNSUBSTANTIATED),
    ("whole_wheat", "Made with 100% whole wheat", Verdict.UNSUBSTANTIATED),
    ("guilt_free", "guilt-free", Verdict.NON_FALSIFIABLE),
]


class PipelineFixtureTests(unittest.TestCase):
    def _run(self, case: str):
        provider = FixtureProvider.for_case(case, FIXTURES_DIR)
        # Image bytes are ignored by the fixture provider — the recorded
        # extraction is returned regardless.
        result = analyze(b"", "image/png", provider, _sources(), image_path=case)
        return result

    def test_high_fibre_substantiated_with_computation(self):
        result = self._run("high_fibre")
        claim = result.claims[0]
        self.assertIs(claim.verdict, Verdict.SUBSTANTIATED)
        self.assertIsNotNone(claim.computation)
        self.assertTrue(claim.computation.passed)
        self.assertEqual(claim.computation.result, 8.2)

    def test_less_oil_unsubstantiated_no_arithmetic(self):
        result = self._run("less_oil")
        claim = result.claims[0]
        self.assertIs(claim.verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(claim.computation)
        # UNSUBSTANTIATED, not CONTRADICTED — the whole point of the case.
        self.assertNotEqual(claim.verdict, Verdict.CONTRADICTED)

    def test_more_protein_unsubstantiated(self):
        result = self._run("more_protein")
        claim = result.claims[0]
        self.assertIs(claim.verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(claim.computation)

    def test_whole_wheat_unsubstantiated_pending_disclosure(self):
        result = self._run("whole_wheat")
        claim = result.claims[0]
        self.assertIs(claim.verdict, Verdict.UNSUBSTANTIATED)
        self.assertIsNone(claim.computation)

    def test_guilt_free_non_falsifiable(self):
        result = self._run("guilt_free")
        claim = result.claims[0]
        self.assertIs(claim.verdict, Verdict.NON_FALSIFIABLE)

    def test_every_claim_records_requirements_and_evidence(self):
        for case, _claim_text, _verdict in CASES:
            with self.subTest(case=case):
                result = self._run(case)
                claim = result.claims[0]
                # SUBJECTIVE_MARKETING is allowed to have zero requirements.
                if _verdict is Verdict.NON_FALSIFIABLE:
                    self.assertEqual(claim.evidence_requirements, [])
                    self.assertEqual(claim.available_evidence, [])
                else:
                    self.assertTrue(claim.evidence_requirements)
                    self.assertEqual(
                        len(claim.evidence_requirements),
                        len(claim.available_evidence),
                    )


if __name__ == "__main__":
    unittest.main()
