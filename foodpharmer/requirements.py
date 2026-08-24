"""Stage 3: :class:`NormalizedClaim` -> list of :class:`EvidenceRequirement`.

Deterministic — keyed on ``claim_type`` and the payload. No LLM.

The requirements a claim generates are what makes the reasoning chain
auditable: a reader can see exactly what evidence the system asked for and
which of it turned out to be available.
"""

from __future__ import annotations

from .models import (
    ClaimType,
    ComparativePayload,
    CompositionPayload,
    EvidenceRequirement,
    NormalizedClaim,
    NutrientContentPayload,
    RequirementType,
)


def derive_requirements(claim: NormalizedClaim) -> list[EvidenceRequirement]:
    """Return the evidence a resolver would need to evaluate this claim."""

    payload = claim.payload
    match claim.claim_type:
        case ClaimType.NUTRIENT_CONTENT:
            assert isinstance(payload, NutrientContentPayload)
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.NUTRIENT_VALUE,
                    description=f"Declared value of {payload.nutrient} on the package.",
                    source_hint="packaging",
                ),
                EvidenceRequirement(
                    requirement_type=RequirementType.FSSAI_THRESHOLD,
                    description=(
                        f"FSSAI qualifying criterion for a '{payload.qualifier} "
                        f"{payload.nutrient}' claim."
                    ),
                    source_hint="fssai",
                ),
            ]

        case ClaimType.COMPARATIVE:
            assert isinstance(payload, ComparativePayload)
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.NUTRIENT_VALUE,
                    description=f"Product {payload.metric} content.",
                    source_hint="packaging",
                ),
                EvidenceRequirement(
                    requirement_type=RequirementType.COMPARATOR_DATA,
                    description=(
                        f"{payload.metric} content of comparable products matching "
                        f"'{payload.baseline_description}', on a comparable measurement basis."
                    ),
                    source_hint="comparator_products",
                ),
            ]

        case ClaimType.COMPOSITION:
            assert isinstance(payload, CompositionPayload)
            requirements = [
                EvidenceRequirement(
                    requirement_type=RequirementType.INGREDIENT_LIST,
                    description=f"Visible ingredient list confirming presence of {payload.component}.",
                    source_hint="packaging",
                )
            ]
            if payload.claimed_percentage is not None:
                requirements.append(
                    EvidenceRequirement(
                        requirement_type=RequirementType.DECLARED_PERCENTAGE,
                        description=(
                            f"Label disclosure of the {payload.component} percentage "
                            f"(claimed {payload.claimed_percentage}%)."
                        ),
                        source_hint="packaging",
                    )
                )
            return requirements

        case ClaimType.ABSENCE:
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.INGREDIENT_LIST,
                    description="Complete ingredient list from the package.",
                    source_hint="packaging",
                )
            ]

        case ClaimType.QUANTITATIVE:
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.NUTRIENT_VALUE,
                    description="Declared value on the package.",
                    source_hint="packaging",
                )
            ]

        case ClaimType.SUPERLATIVE:
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.MARKET_RANKING,
                    description="Authoritative market ranking supporting the superlative claim.",
                    source_hint="market_data",
                )
            ]

        case ClaimType.SCIENTIFIC:
            # No codified evidence source yet — we still record the ask so it
            # is visible in the audit trail.
            return [
                EvidenceRequirement(
                    requirement_type=RequirementType.MARKET_RANKING,
                    description="Peer-reviewed scientific source supporting the mechanism.",
                    source_hint=None,
                )
            ]

        case ClaimType.SUBJECTIVE_MARKETING:
            # Non-falsifiable — no evidence lookup will be attempted.
            return []

    raise ValueError(f"Unhandled ClaimType: {claim.claim_type}")
