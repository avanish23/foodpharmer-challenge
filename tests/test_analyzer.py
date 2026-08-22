import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from foodpharmer.analyzer import analyze_package
from foodpharmer.models import (
    ClaimDecision,
    ClassificationDecision,
    ExtractedClaim,
    NutritionFact,
    PackageExtraction,
    RuleEvidence,
    Verdict,
)


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def parse(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(output_parsed=self.outputs.pop(0))


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


class StaticRetriever:
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = []

    def retrieve(self, claim, context, limit=3):
        self.calls.append((claim, context, limit))
        return self.evidence


class AnalyzePackageTests(unittest.TestCase):
    def test_evaluates_claim_using_retrieved_evidence_and_scores_locally(self):
        extraction = PackageExtraction(
            nutrition_facts=[NutritionFact(nutrient="Protein", value="10 g per 100 g")],
            ingredients=["Wheat flour", "Palm oil"],
            ingredient_list_complete=True,
            claims=[ExtractedClaim(claim="PROTEIN SOURCE", visible_evidence=["PROTEIN SOURCE"])],
        )
        decision = ClaimDecision(
            verdict=Verdict.SUPPORTED,
            rationale="The visible protein amount meets the retrieved criterion.",
            evidence_indexes=[0],
            regulatory_classifications=[
                ClassificationDecision(
                    classification="Protein source",
                    rationale="The visible protein amount meets the retrieved criterion.",
                    evidence_indexes=[0],
                )
            ],
        )
        evidence = [
            RuleEvidence(
                document="FSSAI Claims",
                source="claims.pdf",
                page_number=2,
                section="SCHEDULE I",
                text="A protein source claim requires the stated qualifying amount.",
            )
        ]
        client = FakeClient([extraction, decision])
        retriever = StaticRetriever(evidence)

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "package.png"
            image_path.write_bytes(b"fake-image")
            result = analyze_package(image_path, retriever, client=client)

        self.assertEqual(result.marketing_gap_score, 0.0)
        self.assertEqual(result.claims[0].fssai_evidence, evidence)
        self.assertEqual(result.claims[0].applicable_rule, "FSSAI Claims, page 2, SCHEDULE I")
        self.assertEqual(result.regulatory_classifications[0].classification, "Protein source")
        self.assertEqual(result.regulatory_classifications[0].fssai_evidence, evidence)
        self.assertEqual(len(client.responses.requests), 2)
        self.assertIn("Indexed retrieved FSSAI evidence", client.responses.requests[1]["input"][0]["content"])

    def test_returns_insufficient_information_without_relevant_rule(self):
        extraction = PackageExtraction(
            nutrition_facts=[],
            ingredients=["Wheat flour", "Palm oil"],
            ingredient_list_complete=True,
            claims=[ExtractedClaim(claim="0% Maida", visible_evidence=["0% Maida"])],
        )
        client = FakeClient([extraction])

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "package.png"
            image_path.write_bytes(b"fake-image")
            result = analyze_package(image_path, StaticRetriever([]), client=client)

        self.assertEqual(result.claims[0].verdict, Verdict.INSUFFICIENT_INFORMATION)
        self.assertEqual(result.claims[0].fssai_evidence, [])
        self.assertEqual(result.claims[0].ingredient_list_check.status, "NOT_LISTED")
        self.assertIsNone(result.marketing_gap_score)
        self.assertEqual(len(client.responses.requests), 1)


if __name__ == "__main__":
    unittest.main()
