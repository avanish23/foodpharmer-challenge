"""Small helpers for building synthetic evidence in resolver tests."""

from foodpharmer.models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
    RequirementType,
)


def evidence(
    kind: RequirementType,
    *,
    available: bool,
    data: dict | None = None,
    source: str = "test",
) -> GatheredEvidence:
    return GatheredEvidence(
        requirement=EvidenceRequirement(
            requirement_type=kind, description=f"synthetic {kind.value}", source_hint=source
        ),
        status=EvidenceStatus.AVAILABLE if available else EvidenceStatus.UNAVAILABLE,
        data=data,
        source=source,
    )


def empty_extraction() -> PackageExtraction:
    return PackageExtraction(ingredient_list_complete=False)
