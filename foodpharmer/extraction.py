"""Stage 1: image bytes -> :class:`PackageExtraction` (verbatim label content).

The extraction step is intentionally free of verdicts, thresholds, or FSSAI
interpretation. Its only job is to convert what is visible on the label into
structured text the rest of the pipeline can reason about.
"""

from __future__ import annotations

from .models import PackageExtraction
from .providers.base import LLMProvider


def extract_package(
    image_bytes: bytes, media_type: str, provider: LLMProvider
) -> PackageExtraction:
    """Delegate vision extraction to the provider — no further processing."""

    return provider.extract_package(image_bytes, media_type)
