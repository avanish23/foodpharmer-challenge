"""Provider Protocol — narrows what the LLM is responsible for."""

from __future__ import annotations

from typing import Protocol

from ..models import ClaimResult, NormalizedClaim, PackageExtraction


class LLMProvider(Protocol):
    """The LLM is used for vision extraction, classification, and prose only."""

    def extract_package(
        self, images: list[tuple[bytes, str]]
    ) -> PackageExtraction:
        """Return the verbatim label content — no verdicts.

        ``images`` is one or more ``(image_bytes, media_type)`` tuples of the
        same product pack (e.g. front + back). Implementations must merge the
        visible content across images into a single :class:`PackageExtraction`.
        """

    def normalize_claim(
        self, raw_claim: str, extraction: PackageExtraction
    ) -> NormalizedClaim:
        """Classify one claim and fill the claim-type-specific payload."""

    def explain_verdict(self, claim_result: ClaimResult) -> str:
        """Produce a human-readable reason string for the audit trail.

        Implementations may either call an LLM or synthesize a template — the
        Protocol does not care as long as the caller receives a string.
        """
