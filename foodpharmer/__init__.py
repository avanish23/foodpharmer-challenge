"""Evidence-driven marketing-claim analysis for packaged food.

The pipeline separates four concepts:

    Claim   → what the package asserts
    Requirement → what evidence would substantiate it
    Evidence → what evidence is actually available
    Verdict → what the evidence lets us conclude

See :mod:`foodpharmer.pipeline` for the orchestrator and :mod:`foodpharmer.models`
for the auditable JSON schema.
"""

from .models import (
    ClaimAnalysisResult,
    ClaimResult,
    ClaimType,
    Computation,
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    NormalizedClaim,
    RequirementType,
    Verdict,
)

__all__ = [
    "ClaimAnalysisResult",
    "ClaimResult",
    "ClaimType",
    "Computation",
    "EvidenceRequirement",
    "EvidenceStatus",
    "GatheredEvidence",
    "NormalizedClaim",
    "RequirementType",
    "Verdict",
]
