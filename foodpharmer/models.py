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


class IngredientListCheckStatus(str, Enum):
    """Factual result of matching an ingredient-absence claim to the label."""

    LISTED = "LISTED"
    NOT_LISTED = "NOT_LISTED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class NutritionFact(StrictModel):
    """A nutrition fact visibly present on the package."""

    nutrient: str = Field(description="The nutrient or nutrition-label field as printed.")
    value: str = Field(description="The complete visible value, including units and serving basis.")


class RuleEvidence(StrictModel):
    """A verbatim local FSSAI source chunk used in an evaluation."""

    document: str = Field(description="Document title or filename.")
    source: str = Field(description="Local source path relative to the FSSAI data directory.")
    page_number: int = Field(description="One-based PDF page number.")
    section: str | None = Field(description="Detected section or schedule heading, if available.")
    text: str = Field(description="Verbatim retrieved source text.")


class ExtractedClaim(StrictModel):
    """A visible, atomic marketing claim before it is evaluated."""

    claim: str = Field(description="The exact visible marketing claim, without paraphrasing.")
    visible_evidence: list[str] = Field(
        description="Exact visible label text or nutrition facts relevant to this claim."
    )


class IngredientListCheck(StrictModel):
    """A deterministic ingredient-list consistency check, not a compliance verdict."""

    status: IngredientListCheckStatus
    terms_checked: list[str]
    evidence: list[str] = Field(
        description="Exact visible ingredient entries used for this factual check."
    )


class ClaimAssessment(ExtractedClaim):
    """One marketing claim evaluated against retrieved FSSAI evidence."""

    verdict: Verdict
    rationale: str = Field(
        description=(
            "Brief explanation using only visible package information and retrieved FSSAI evidence. "
            "State what information or criterion is missing when insufficient."
        )
    )
    applicable_rule: str | None = Field(
        description="A source label derived from the retrieved FSSAI evidence, or null if none applies.",
    )
    fssai_evidence: list[RuleEvidence] = Field(
        description="Retrieved FSSAI chunks selected as evidence for this verdict."
    )
    ingredient_list_check: IngredientListCheck | None = Field(
        description="Separate factual ingredient-list check, or null when not applicable."
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
        description="A source label derived from retrieved FSSAI evidence that defines this classification."
    )
    fssai_evidence: list[RuleEvidence] = Field(
        description="Retrieved FSSAI chunks selected as evidence for this classification."
    )


class PackageExtraction(StrictModel):
    """Structured extraction output; deliberately contains no regulatory result."""

    nutrition_facts: list[NutritionFact]
    ingredients: list[str]
    ingredient_list_complete: bool
    claims: list[ExtractedClaim]


class ClaimDecision(StrictModel):
    """A model decision referencing only indexes of supplied evidence."""

    verdict: Verdict
    rationale: str
    evidence_indexes: list[int] = Field(
        description="Zero-based indexes of retrieved FSSAI evidence used for the decision."
    )
    regulatory_classifications: list["ClassificationDecision"]


class ClassificationDecision(StrictModel):
    """A classification decision referencing only supplied evidence indexes."""

    classification: str
    rationale: str
    evidence_indexes: list[int]


class AnalysisResult(StrictModel):
    """Final API/CLI response, with its score calculated locally."""

    nutrition_facts: list[NutritionFact]
    ingredients: list[str]
    ingredient_list_complete: bool
    claims: list[ClaimAssessment]
    regulatory_classifications: list[RegulatoryClassification]
    marketing_gap_score: float | None = Field(
        description="Percentage of assessable claims that are NOT_SUPPORTED, or null."
    )
