"""Offline fixture provider — reads recorded LLM responses from disk.

Each canonical case lives under ``tests/fixtures/<case>/`` with an
``extract.json`` (a :class:`PackageExtraction` dump) and a ``normalize.json``
(a ``{claim_text: NormalizedClaim}`` mapping keyed by the exact visible claim
string). Tests and the demo point at these fixtures so pipeline behavior is
reproducible without paying for API calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import ClaimResult, NormalizedClaim, PackageExtraction


class FixtureProvider:
    """Provider that never calls an LLM — all responses come from JSON files."""

    def __init__(
        self,
        extraction: PackageExtraction,
        normalizations: dict[str, NormalizedClaim],
        case: str | None = None,
    ) -> None:
        self._extraction = extraction
        self._normalizations = normalizations
        self._case = case

    @classmethod
    def for_case(cls, case: str, fixtures_dir: str | Path) -> "FixtureProvider":
        case_dir = Path(fixtures_dir) / case
        extract_path = case_dir / "extract.json"
        normalize_path = case_dir / "normalize.json"
        if not extract_path.exists():
            raise FileNotFoundError(f"Missing fixture {extract_path}")
        if not normalize_path.exists():
            raise FileNotFoundError(f"Missing fixture {normalize_path}")

        extraction = PackageExtraction.model_validate_json(extract_path.read_text("utf-8"))
        raw_map = json.loads(normalize_path.read_text("utf-8"))
        normalizations = {
            claim_text: NormalizedClaim.model_validate(payload)
            for claim_text, payload in raw_map.items()
        }
        return cls(extraction=extraction, normalizations=normalizations, case=case)

    # ------------------------------------------------------------------
    # LLMProvider protocol
    # ------------------------------------------------------------------

    def extract_package(self, image_bytes: bytes, media_type: str) -> PackageExtraction:
        return self._extraction

    def normalize_claim(
        self, raw_claim: str, extraction: PackageExtraction
    ) -> NormalizedClaim:
        try:
            return self._normalizations[raw_claim]
        except KeyError as error:
            available = ", ".join(sorted(self._normalizations)) or "<none>"
            raise KeyError(
                f"FixtureProvider (case={self._case!r}) has no normalization "
                f"for claim {raw_claim!r}. Available keys: {available}"
            ) from error

    def explain_verdict(self, claim_result: ClaimResult) -> str:
        # Fixture provider never hits an LLM for prose — the resolver's own
        # reason string is authoritative. Callers may still choose to run
        # the LLM ``explain_verdict`` separately.
        return claim_result.reason
