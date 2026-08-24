"""OpenAI-backed provider.

Only imported at runtime by callers that opt in — the tests never touch it.
Uses ``client.responses.parse`` with a Pydantic ``text_format`` so the model
is forced to return schema-conforming structured output.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING

from ..models import ClaimResult, NormalizedClaim, PackageExtraction

if TYPE_CHECKING:  # pragma: no cover - typing only
    from openai import OpenAI


EXTRACTION_PROMPT = """You extract marketing claims and nutrition facts printed on packaged food labels.

Extract only text and nutrition facts actually visible in the image. Marketing
claims include promotional statements such as nutrient-content or comparative
claims. Do NOT treat the following as marketing claims:

* the product name or brand name (e.g. "Ragi Kaju Pista Cookies", "Parle-G")
* ordinary ingredient-list entries
* raw nutrition-table rows or nutrition values
* net weight, batch numbers, MRP, addresses, disclaimers, storage instructions

Preserve claim wording exactly where legible. Split combined marketing
statements into atomic claims whenever each part can be independently assessed.
Include the exact visible evidence for each claim. Do not deduplicate near-
identical claims that appear more than once on the pack — but do NOT invent a
claim that is not visibly present.

Extract ingredients as exact visible entries (comma-separated in the list order
on the pack), separately from claims. Set ingredient_list_complete to true
only when the full ingredient list is visibly present and legible from its
start through its end; otherwise set it to false. Do not assess compliance,
health, or regulatory requirements in this extraction step.
"""


NORMALIZATION_PROMPT = """You classify one visible food-package marketing claim into a claim type and
fill a structured payload. Choose the claim_type using these rules IN ORDER —
apply the first that matches:

1. NUTRIENT_CONTENT — the claim asserts a level of a specific nutrient using a
   qualifier that maps to a FSSAI-style criterion. Trigger words include:
   "high", "low", "source", "source of", "rich", "rich in", "free", "no added".
   Examples:
     - "High Fibre" → NUTRIENT_CONTENT, nutrient="fibre", qualifier="high"
     - "Protein Source" / "Source of Protein" → NUTRIENT_CONTENT, nutrient="protein", qualifier="source"
     - "Rich in Iron" → NUTRIENT_CONTENT, nutrient="iron", qualifier="rich"
     - "Low Sodium" → NUTRIENT_CONTENT, nutrient="sodium", qualifier="low"
   These are NOT SUBJECTIVE_MARKETING even if the qualifier feels vague — a
   downstream resolver will check the FSSAI threshold. Use the singular
   nutrient noun ("fibre", "protein", "sodium").

2. COMPARATIVE — claim references another product / brand / category and asserts
   more/less of a metric ("50% less oil than X", "2x more protein").
   baseline_specified=true ONLY when the claim names a specific comparator
   product, a published category average, or a stated methodology. Phrases
   like "other chips", "leading brands", or "regular variant" are FALSE.

3. ABSENCE — claim asserts an ingredient/component is absent: "No X",
   "0% X", "Zero X", "X-free". Use the shortest canonical form of the
   ingredient in the "ingredient" field (e.g. "maida", "palm oil", "trans fat",
   "added sugar", "cholesterol", "white sugar").

4. COMPOSITION — claim asserts a component is present, often with a percentage.
   "Made with 100% X", "Contains real X". disclosed_on_label=true ONLY when
   the label visibly declares the percentage the claim asserts (a matching %
   next to that ingredient in the ingredient list counts).

5. SUPERLATIVE — "India's #1", "Nation's favourite", ranking-style claims.

6. SCIENTIFIC — "Clinically proven", "Doctor recommended", cited mechanism.

7. QUANTITATIVE — a bare numeric ("10 g protein per serve") with no qualifier.

8. SUBJECTIVE_MARKETING — LAST RESORT. Use only when the claim is a subjective
   emotional/aesthetic descriptor with no measurable property ("guilt-free",
   "wholesome", "delicious", "goodness of X" WITHOUT a nutrient qualifier).
   Do NOT put nutrient-content claims here just because the qualifier is
   informal — "Protein Source" is NUTRIENT_CONTENT, not SUBJECTIVE_MARKETING.

Rules for all types:
* Never fabricate values. Use null when a field is not visible on the label.
* declared_value must be a plain number (float). declared_unit is the unit
  alone ("g", "mg", "kcal") — do NOT put "per 100 g" or "per serve" in the
  unit field; those belong in declared_per.
* Do NOT judge compliance, healthiness, or evidence. That happens later.

Return the schema-conforming NormalizedClaim only.
"""


EXPLAIN_PROMPT = """You produce one plain-language sentence explaining a claim verdict. Use only
the verdict, computation (if any), evidence data, and normalized claim provided.
Do not introduce new facts.
"""


class OpenAIProvider:
    """Live OpenAI provider.

    Constructed lazily — no OpenAI import cost when tests run against fixtures.
    """

    def __init__(
        self,
        client: "OpenAI | None" = None,
        model: str = "gpt-4.1-mini",
        *,
        temperature: float = 0.0,
    ) -> None:
        if client is None:
            from openai import OpenAI  # local import so tests don't need the SDK

            client = OpenAI()
        self._client = client
        self._model = model
        # Pin decoding so the same image → (mostly) the same JSON across runs.
        # The Responses API does not accept a ``seed`` parameter (that's Chat
        # Completions-only), so temperature=0 is the only lever we have here.
        # Determinism is best-effort at the API level regardless.
        self._temperature = temperature

    def _decoding_kwargs(self) -> dict:
        return {"temperature": self._temperature}

    def extract_package(self, image_bytes: bytes, media_type: str) -> PackageExtraction:
        data_url = _data_url(image_bytes, media_type)
        response = self._client.responses.parse(
            model=self._model,
            instructions=EXTRACTION_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_image", "image_url": data_url}],
                }
            ],
            text_format=PackageExtraction,
            **self._decoding_kwargs(),
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI did not return a structured extraction.")
        return parsed

    def normalize_claim(
        self, raw_claim: str, extraction: PackageExtraction
    ) -> NormalizedClaim:
        context = extraction.model_dump_json(exclude={"claims": True})
        response = self._client.responses.parse(
            model=self._model,
            instructions=NORMALIZATION_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Claim to normalize:\n{raw_claim}\n\n"
                                f"Package context JSON:\n{context}"
                            ),
                        }
                    ],
                }
            ],
            text_format=NormalizedClaim,
            **self._decoding_kwargs(),
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI did not return a structured NormalizedClaim.")
        return parsed

    def explain_verdict(self, claim_result: ClaimResult) -> str:
        response = self._client.responses.create(
            model=self._model,
            instructions=EXPLAIN_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": claim_result.model_dump_json(exclude={"reason": True}),
                        }
                    ],
                }
            ],
            **self._decoding_kwargs(),
        )
        return response.output_text.strip()


def _data_url(image_bytes: bytes, media_type: str) -> str:
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(f"Unsupported media type {media_type!r}")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def guess_media_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")
