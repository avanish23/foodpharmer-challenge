"""OpenAI-backed package-claim analysis, separate from scoring logic."""

import base64
from pathlib import Path

from openai import OpenAI

from .models import AnalysisResult, ModelAnalysis
from .scoring import marketing_gap_score


SYSTEM_PROMPT = """You analyze marketing claims printed on packaged food labels.

Your task is only to determine whether each visible marketing claim is supported
by the FSSAI rules supplied in the user message. This is not a health or
nutrition-quality assessment. Do not call a product healthy or unhealthy and do
not offer medical, dietary, or legal advice.

Extract only text and nutrition facts actually visible in the image. Marketing
claims include promotional statements such as nutrient-content or comparative
claims; do not treat ordinary ingredient lists or raw nutrition-table entries as
claims. Preserve claim wording exactly where legible.

Use the supplied rules as the exclusive regulatory source. Never use outside
knowledge, invent a rule, threshold, label value, serving size, or inference.
For every extracted claim, return exactly one allowed verdict. If the supplied
rules do not cover the claim, or the image/rules lack information needed to
apply a rule, use INSUFFICIENT_INFORMATION. Return no claims if none are visible.
"""


def _image_data_url(image_path: str | Path) -> str:
    path = Path(image_path)
    suffix = path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    try:
        media_type = media_types[suffix]
    except KeyError as error:
        raise ValueError("Image must be a JPG, PNG, or WebP file.") from error
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def analyze_package(
    image_path: str | Path,
    fssai_rules: str,
    *,
    model: str = "gpt-4.1-mini",
    client: OpenAI | None = None,
) -> AnalysisResult:
    """Analyze an image against caller-supplied rules and add the local score."""

    if not fssai_rules.strip():
        raise ValueError("Supplied FSSAI rules must not be empty.")

    api_client = client or OpenAI()
    response = api_client.responses.parse(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": f"Supplied FSSAI rules:\n{fssai_rules}"},
                    {"type": "input_image", "image_url": _image_data_url(image_path)},
                ],
            }
        ],
        text_format=ModelAnalysis,
    )
    analysis = response.output_parsed
    if analysis is None:
        raise RuntimeError("The model did not return a structured analysis.")

    return AnalysisResult(
        **analysis.model_dump(),
        marketing_gap_score=marketing_gap_score(claim.verdict for claim in analysis.claims),
    )
