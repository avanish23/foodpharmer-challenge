"""Small helpers shared across resolvers."""

from __future__ import annotations

from ..models import (
    EvidenceStatus,
    GatheredEvidence,
    RequirementType,
)


def find(evidence: list[GatheredEvidence], kind: RequirementType) -> GatheredEvidence | None:
    """Return the first gathered evidence for a given requirement kind, or None."""

    for entry in evidence:
        if entry.requirement.requirement_type is kind:
            return entry
    return None


def available(entry: GatheredEvidence | None) -> bool:
    return entry is not None and entry.status is EvidenceStatus.AVAILABLE
