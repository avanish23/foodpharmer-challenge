"""End-to-end pipeline orchestrator.

Wires the six stages together:

  extract -> normalize -> derive_requirements -> gather -> resolve -> assemble

Nothing in this module performs claim-domain reasoning of its own — the
individual stage modules own that. The pipeline just carries the data through
and produces the top-level :class:`ClaimAnalysisResult`.
"""

from __future__ import annotations

from pathlib import Path

from .evidence.base import EvidenceSource, gather_all
from .extraction import extract_package
from .models import (
    ClaimAnalysisResult,
    ClaimResult,
    NormalizedClaim,
    PackageExtraction,
)
from .normalization import normalize_claims
from .providers.base import LLMProvider
from .requirements import derive_requirements
from .resolvers.base import resolve_claim


def analyze(
    image_bytes: bytes,
    media_type: str,
    provider: LLMProvider,
    evidence_sources: list[EvidenceSource],
    *,
    image_path: str | Path = "",
) -> ClaimAnalysisResult:
    """Run the full pipeline for one image and return the audit trail."""

    extraction = extract_package(image_bytes, media_type, provider)
    normalized = normalize_claims(extraction, provider)
    claim_results = [
        _run_one_claim(claim, extraction, evidence_sources) for claim in normalized
    ]
    return ClaimAnalysisResult(
        image_path=str(image_path),
        extraction=extraction,
        claims=claim_results,
    )


def _run_one_claim(
    claim: NormalizedClaim,
    extraction: PackageExtraction,
    evidence_sources: list[EvidenceSource],
) -> ClaimResult:
    requirements = derive_requirements(claim)
    evidence = gather_all(requirements, extraction, evidence_sources)
    verdict, reason, computation = resolve_claim(claim, evidence, extraction)
    return ClaimResult(
        claim_text=claim.claim_text,
        claim_type=claim.claim_type,
        normalized_claim=claim,
        evidence_requirements=requirements,
        available_evidence=evidence,
        verdict=verdict,
        reason=reason,
        computation=computation,
    )
