"""Structured data models exchanged with the OpenAI API and CLI."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base schema that rejects fields outside the documented V1 contract."""

    model_config = ConfigDict(extra="forbid")


class Verdict(str, Enum):
    """The only claim outcomes allowed in V1."""

    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class NutritionFact(StrictModel):
    """A nutrition fact visibly present on the package."""

    nutrient: str = Field(description="The nutrient or nutrition-label field as printed.")
    value: str = Field(description="The complete visible value, including units and serving basis.")


class ClaimAssessment(StrictModel):
    """One visible marketing claim and its evaluation against supplied rules."""

    claim: str = Field(description="The exact visible marketing claim, without paraphrasing.")
    visible_evidence: list[str] = Field(
        description="Exact visible label text or nutrition facts relevant to this claim."
    )
    verdict: Verdict
    rationale: str = Field(
        description=(
            "Brief explanation using only visible package information and supplied rules. "
            "State what information or criterion is missing when insufficient."
        )
    )
    applicable_rule: str | None = Field(
        description="The exact supplied rule used, or null if no supplied rule applies.",
    )


class RegulatoryClassification(StrictModel):
    """A supplied-rule classification evaluated from visible package facts."""

    classification: str = Field(
        description="The exact classification name defined in the supplied FSSAI rules."
    )
    visible_evidence: list[str] = Field(
        description="Exact visible nutrition facts or label text used for this classification."
    )
    rationale: str = Field(
        description="Brief explanation using only the visible evidence and supplied rule."
    )
    applicable_rule: str = Field(
        description="The exact supplied rule that defines this classification."
    )


class ModelAnalysis(StrictModel):
    """Structured output the model returns; deliberately excludes the score."""

    nutrition_facts: list[NutritionFact]
    claims: list[ClaimAssessment]
    regulatory_classifications: list[RegulatoryClassification]


class AnalysisResult(ModelAnalysis):
    """Final API/CLI response, with its score calculated locally."""

    marketing_gap_score: float | None = Field(
        description="Percentage of assessable claims that are NOT_SUPPORTED, or null."
    )
