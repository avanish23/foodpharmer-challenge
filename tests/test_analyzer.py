import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from foodpharmer.analyzer import analyze_package
from foodpharmer.models import (
    ClaimAssessment,
    ModelAnalysis,
    RegulatoryClassification,
    Verdict,
)


class FakeResponses:
    def __init__(self, analysis):
        self.analysis = analysis
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.analysis)


class FakeClient:
    def __init__(self, analysis):
        self.responses = FakeResponses(analysis)


class AnalyzePackageTests(unittest.TestCase):
    def test_score_uses_claims_not_regulatory_classifications(self):
        analysis = ModelAnalysis(
            nutrition_facts=[],
            claims=[
                ClaimAssessment(
                    claim="No cholesterol",
                    visible_evidence=["Cholesterol: 0 mg"],
                    verdict=Verdict.SUPPORTED,
                    rationale="The supplied criterion is met.",
                    applicable_rule="Cholesterol claim criterion",
                )
            ],
            regulatory_classifications=[
                RegulatoryClassification(
                    classification="High in sugar",
                    visible_evidence=["Total sugar: 15 g per 100 g"],
                    rationale="The supplied threshold is met.",
                    applicable_rule="High-sugar threshold",
                )
            ],
        )
        client = FakeClient(analysis)

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "package.png"
            image_path.write_bytes(b"not-an-image-needed-by-fake-client")
            result = analyze_package(image_path, "Supplied rule text", client=client)

        self.assertEqual(result.marketing_gap_score, 0.0)
        self.assertEqual(result.regulatory_classifications[0].classification, "High in sugar")
        self.assertIs(client.responses.kwargs["text_format"], ModelAnalysis)


if __name__ == "__main__":
    unittest.main()
