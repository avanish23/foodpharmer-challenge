"""Pydantic models for evidence-driven claim analysis.

These types are the auditable JSON contract of the whole pipeline. The design
keeps four concepts distinct so a reader of the output can follow the reasoning
end to end:

* ``ExtractedClaim`` / ``PackageExtraction`` — what the label actually says
* ``NormalizedClaim`` — what the label is asserting, typed and structured
* ``EvidenceRequirement`` — what would be needed to verify the assertion
* ``GatheredEvidence`` — what evidence was actually available
* ``Verdict`` and ``Computation`` — what the evidence lets us conclude, and any
  arithmetic that produced the conclusion

The verdict enum has four values (SUBSTANTIATED / CONTRADICTED /
UNSUBSTANTIATED / NON_FALSIFIABLE) — UNSUBSTANTIATED is NOT FALSE, and this
distinction is enforced by the resolvers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base schema — rejects unknown fields to keep the JSON contract tight."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Verdict(str, Enum):
    """The four allowed outcomes of a claim evaluation.

    * ``SUBSTANTIATED`` — available evidence supports the claim.
    * ``CONTRADICTED`` — available evidence actually conflicts with the claim.
    * ``UNSUBSTANTIATED`` — the claim MAY be true, but the evidence needed to
      verify it is unavailable. NOT the same as FALSE.
    * ``NON_FALSIFIABLE`` — the claim is subjective/vague and cannot be
      objectively evaluated.
    """

    SUBSTANTIATED = "SUBSTANTIATED"
    CONTRADICTED = "CONTRADICTED"
    UNSUBSTANTIATED = "UNSUBSTANTIATED"
    NON_FALSIFIABLE = "NON_FALSIFIABLE"


class ClaimType(str, Enum):
    """Coarse category assigned by the normalizer before evaluation.

    This taxonomy is expected to evolve as real-world claims expose gaps. Each
    ClaimType has its own payload shape and its own resolver.
    """

    NUTRIENT_CONTENT = "NUTRIENT_CONTENT"
    COMPARATIVE = "COMPARATIVE"
    COMPOSITION = "COMPOSITION"
    ABSENCE = "ABSENCE"
    QUANTITATIVE = "QUANTITATIVE"
    SUPERLATIVE = "SUPERLATIVE"
    SCIENTIFIC = "SCIENTIFIC"
    SUBJECTIVE_MARKETING = "SUBJECTIVE_MARKETING"


class EvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class RequirementType(str, Enum):
    """The kinds of evidence a claim might require.

    Each requirement is dispatched to whichever :class:`EvidenceSource` can
    fulfill it; sources unable to answer report UNAVAILABLE rather than
    guessing.
    """

    NUTRIENT_VALUE = "NUTRIENT_VALUE"
    FSSAI_THRESHOLD = "FSSAI_THRESHOLD"
    INGREDIENT_LIST = "INGREDIENT_LIST"
    DECLARED_PERCENTAGE = "DECLARED_PERCENTAGE"
    COMPARATOR_DATA = "COMPARATOR_DATA"
    MARKET_RANKING = "MARKET_RANKING"


class IngredientListCheckStatus(str, Enum):
    """Factual result of a ``0% ingredient`` label-consistency check."""

    LISTED = "LISTED"
    NOT_LISTED = "NOT_LISTED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


# ---------------------------------------------------------------------------
# Package-extraction primitives (reused from V2)
# ---------------------------------------------------------------------------


class NutritionFact(StrictModel):
    """A nutrition fact visibly present on the package."""

    nutrient: str = Field(description="The nutrient or nutrition-label field as printed.")
    value: str = Field(description="The complete visible value, including units and serving basis.")


class ExtractedClaim(StrictModel):
    """A visible, atomic marketing claim before it is evaluated."""

    claim: str = Field(description="The exact visible marketing claim, without paraphrasing.")
    visible_evidence: list[str] = Field(
        default_factory=list,
        description="Exact visible label text or nutrition facts relevant to this claim.",
    )


class PackageExtraction(StrictModel):
    """Vision-extracted, verbatim label content — no verdicts yet."""

    nutrition_facts: list[NutritionFact] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    ingredient_list_complete: bool = Field(
        description="True only when the entire ingredient list is visibly present and legible."
    )
    claims: list[ExtractedClaim] = Field(default_factory=list)


class RuleEvidence(StrictModel):
    """A verbatim source chunk retrieved from the local FSSAI corpus."""

    document: str
    source: str
    page_number: int
    section: str | None = None
    text: str


class IngredientListCheck(StrictModel):
    """A deterministic ingredient-list consistency check.

    Not a verdict — resolvers consume this alongside other evidence.
    """

    status: IngredientListCheckStatus
    terms_checked: list[str]
    evidence: list[str]


# ---------------------------------------------------------------------------
# Claim-type payloads
# ---------------------------------------------------------------------------
#
# Every NormalizedClaim carries a ``claim_type`` tag and a payload whose shape
# is specific to that tag. The union below is a discriminated union — Pydantic
# dispatches to the right payload class from the ``claim_type`` field.
#
# Rule of thumb for payload design: fields the resolver needs to make a
# verdict without going back to the raw claim text.
# ---------------------------------------------------------------------------


class _PayloadBase(StrictModel):
    """Common base for all claim-type payloads. The ``claim_type`` tag drives
    the discriminated union used inside :class:`NormalizedClaim`."""


class NutrientContentPayload(_PayloadBase):
    """e.g. "High Fibre", "Rich in Protein", "Low Sugar".

    Resolver needs: qualifier keyword (high/low/source), the nutrient name to
    look up a threshold, and (when visible) the declared value so arithmetic
    can be performed in Python.
    """

    claim_type: Literal[ClaimType.NUTRIENT_CONTENT] = ClaimType.NUTRIENT_CONTENT
    nutrient: str = Field(description='Nutrient the claim references, e.g. "dietary fibre".')
    qualifier: str = Field(description='Qualifying word, e.g. "high", "low", "source of", "rich in".')
    declared_value: float | None = Field(
        default=None,
        description="Numeric nutrient value if visible on the package.",
    )
    declared_unit: str | None = Field(default=None, description='Unit of the declared value, e.g. "g".')
    declared_per: str | None = Field(
        default=None, description='Basis of the declared value, e.g. "per 100g".'
    )


class ComparativePayload(_PayloadBase):
    """e.g. "50% less oil than other chips", "2x more protein".

    ``baseline_specified`` is the critical field: a vague baseline
    ("other chips") means the claim can never be SUBSTANTIATED, but the
    resolver must not label it CONTRADICTED either — the verdict is
    UNSUBSTANTIATED.
    """

    claim_type: Literal[ClaimType.COMPARATIVE] = ClaimType.COMPARATIVE
    metric: str = Field(description='Metric being compared, e.g. "oil", "protein", "sugar".')
    magnitude: float = Field(description='Numeric magnitude, e.g. 50.0 for "50%", 2.0 for "2x".')
    magnitude_unit: Literal["percent", "multiplier", "absolute"]
    direction: Literal["less", "more"]
    baseline_description: str = Field(description='Verbatim baseline phrase, e.g. "other chips".')
    baseline_specified: bool = Field(
        description=(
            "True only if the baseline names a specific product, methodology, or a published "
            "category average. Vague phrases like 'other chips' or 'regular brands' are False."
        )
    )
    measurement_basis: str | None = Field(
        default=None, description='Basis for comparison, e.g. "per 100g".'
    )


class CompositionPayload(_PayloadBase):
    """e.g. "Made with 100% whole wheat", "Contains real fruit".

    ``disclosed_on_label`` is True only when the label visibly discloses the
    ingredient percentage — an unqualified "100%" without a % breakdown cannot
    be SUBSTANTIATED from the ingredient list alone.
    """

    claim_type: Literal[ClaimType.COMPOSITION] = ClaimType.COMPOSITION
    component: str = Field(description='Ingredient or component asserted, e.g. "whole wheat".')
    claimed_percentage: float | None = Field(
        default=None, description="Explicit percentage in the claim, or None."
    )
    percentage_qualifier: str | None = Field(
        default=None, description='e.g. "100%", "made with", "contains".'
    )
    disclosed_on_label: bool = Field(
        description="True only if the actual % of the component is visibly declared on the label."
    )


class AbsencePayload(_PayloadBase):
    """e.g. "No added sugar", "0% maida", "Trans fat free"."""

    claim_type: Literal[ClaimType.ABSENCE] = ClaimType.ABSENCE
    ingredient: str
    claim_form: str = Field(description="Verbatim surface form of the absence claim.")
    zero_percent: bool = Field(description='True for the "0% X" surface form.')


class SubjectiveMarketingPayload(_PayloadBase):
    """e.g. "guilt-free", "wholesome goodness", "feel-good snack"."""

    claim_type: Literal[ClaimType.SUBJECTIVE_MARKETING] = ClaimType.SUBJECTIVE_MARKETING
    phrase: str
    reason_non_falsifiable: str = Field(
        description="Brief LLM-supplied reason the phrase cannot be evaluated objectively."
    )


class QuantitativePayload(_PayloadBase):
    """A bare numeric assertion, e.g. "10g protein per serve"."""

    claim_type: Literal[ClaimType.QUANTITATIVE] = ClaimType.QUANTITATIVE
    metric: str
    value: float
    unit: str
    per_basis: str | None = None


class SuperlativePayload(_PayloadBase):
    """e.g. "India's #1 chips", "The nation's favourite"."""

    claim_type: Literal[ClaimType.SUPERLATIVE] = ClaimType.SUPERLATIVE
    claim_phrase: str
    domain: str | None = None


class ScientificPayload(_PayloadBase):
    """e.g. "Clinically proven to lower cholesterol"."""

    claim_type: Literal[ClaimType.SCIENTIFIC] = ClaimType.SCIENTIFIC
    claim_phrase: str
    cited_evidence: str | None = None


# OpenAI structured-output schemas reject `oneOf`, which Pydantic emits when a
# Union has an explicit ``discriminator=``. Use a plain Union — every payload
# still carries its own ``Literal[ClaimType.X]`` tag, so validation still
# dispatches to the correct payload class from the ``claim_type`` field.
NormalizedPayload = Union[
    NutrientContentPayload,
    ComparativePayload,
    CompositionPayload,
    AbsencePayload,
    QuantitativePayload,
    SuperlativePayload,
    ScientificPayload,
    SubjectiveMarketingPayload,
]


class NormalizedClaim(StrictModel):
    """One claim classified and structured for deterministic evaluation."""

    claim_text: str = Field(description="The exact visible claim text.")
    claim_type: ClaimType
    payload: NormalizedPayload


# ---------------------------------------------------------------------------
# Evidence + verdict types
# ---------------------------------------------------------------------------


class EvidenceRequirement(StrictModel):
    """Description of one piece of evidence needed to evaluate a claim."""

    requirement_type: RequirementType
    description: str
    source_hint: str | None = Field(
        default=None,
        description='Preferred source id, e.g. "packaging", "fssai", "comparator_products".',
    )


class GatheredEvidence(StrictModel):
    """The outcome of asking one evidence source to fulfill one requirement.

    ``data`` is a free-form JSON blob whose shape depends on ``requirement_type``:
    a nutrient row, a list of :class:`RuleEvidence`, an ingredient list, etc.
    ``status`` explicitly separates "evidence was found" from "evidence is
    absent" — the resolvers rely on this to avoid conflating unavailable with
    contradictory.
    """

    requirement: EvidenceRequirement
    status: EvidenceStatus
    data: dict[str, Any] | None = None
    source: str = Field(description="source_id of the evidence source that answered.")
    note: str | None = Field(
        default=None,
        description="Optional short explanation, e.g. why evidence was unavailable.",
    )


class Computation(StrictModel):
    """Deterministic arithmetic performed by a resolver.

    Recorded for auditability — the reader can reproduce the number.
    """

    operation: str = Field(
        description=(
            "Identifier of the operation performed, "
            'e.g. "percentage_reduction", "threshold_check", "multiplier_check".'
        )
    )
    inputs: dict[str, Any]
    result: float | None = None
    unit: str | None = None
    passed: bool | None = Field(
        default=None,
        description="Whether the claim arithmetic holds against the evidence.",
    )


class ClaimResult(StrictModel):
    """The full audit trail for one claim: normalization → requirements →
    evidence → verdict → reason. This is the primary output artifact."""

    claim_text: str
    claim_type: ClaimType
    normalized_claim: NormalizedClaim
    evidence_requirements: list[EvidenceRequirement]
    available_evidence: list[GatheredEvidence]
    verdict: Verdict
    reason: str
    computation: Computation | None = None


class ClaimAnalysisResult(StrictModel):
    """Top-level output for a single package image."""

    image_path: str
    extraction: PackageExtraction
    claims: list[ClaimResult]


__all__ = [
    "AbsencePayload",
    "ClaimAnalysisResult",
    "ClaimResult",
    "ClaimType",
    "ComparativePayload",
    "CompositionPayload",
    "Computation",
    "EvidenceRequirement",
    "EvidenceStatus",
    "ExtractedClaim",
    "GatheredEvidence",
    "IngredientListCheck",
    "IngredientListCheckStatus",
    "NormalizedClaim",
    "NormalizedPayload",
    "NutrientContentPayload",
    "NutritionFact",
    "PackageExtraction",
    "QuantitativePayload",
    "RequirementType",
    "RuleEvidence",
    "ScientificPayload",
    "StrictModel",
    "SubjectiveMarketingPayload",
    "SuperlativePayload",
    "Verdict",
]
