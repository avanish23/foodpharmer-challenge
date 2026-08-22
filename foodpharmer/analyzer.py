"""OpenAI-backed package-claim analysis, separate from scoring logic."""

import base64
from collections.abc import Iterable
from pathlib import Path

from openai import OpenAI

from .models import (
    AnalysisResult,
    ClaimAssessment,
    ClaimDecision,
    PackageExtraction,
    RegulatoryClassification,
    RuleEvidence,
    Verdict,
)
from .ingredient_checks import check_ingredient_list
from .retrieval import FssaiRuleRetriever
from .scoring import marketing_gap_score


EXTRACTION_PROMPT = """You extract marketing claims and nutrition facts printed on packaged food labels.

Extract only text and nutrition facts actually visible in the image. Marketing
claims include promotional statements such as nutrient-content or comparative
claims; do not treat ordinary ingredient lists or raw nutrition-table entries as
claims. Preserve claim wording exactly where legible. Split combined marketing
statements into atomic claims whenever each part can be independently assessed.
For example, a label that separately claims no cholesterol, no white sugar, and
no trans fat must produce three claim records, not one combined record. Include
the exact visible evidence for each claim. Do not assess compliance, health, or
regulatory requirements in this extraction step.

Extract the ingredients as exact visible entries, separately from claims. Set
ingredient_list_complete to true only when the full ingredient list is visibly
present and legible from its start through its end; otherwise set it to false.
"""

EVALUATION_PROMPT = """You evaluate one visible food-package marketing claim against retrieved FSSAI evidence.

Use only the claim, visible label information, and the indexed FSSAI evidence in
the user message. Never use outside knowledge, invent a rule, threshold, label
value, serving size, or inference. Return SUPPORTED only when selected evidence
supports the claim's stated criteria. Return NOT_SUPPORTED only when selected
evidence explicitly establishes that a criterion fails. Return
INSUFFICIENT_INFORMATION when no selected evidence is sufficient or the label
lacks information needed to apply it. The absence of an ingredient is not proof
unless the selected evidence says it is sufficient.

Set evidence_indexes only to indexes from the supplied list that you actually
used. Separately return regulatory classifications only when selected evidence
explicitly defines the classification and visible nutrition facts meet its
criteria. Use evidence indexes for each classification too. Do not make health,
dietary, legal, or overall-quality judgments.
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
    retriever: FssaiRuleRetriever,
    *,
    model: str = "gpt-4.1-mini",
    client: OpenAI | None = None,
) -> AnalysisResult:
    """Analyze an image using rule evidence retrieved from the local FSSAI corpus."""

    api_client = client or OpenAI()
    response = api_client.responses.parse(
        model=model,
        instructions=EXTRACTION_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": _image_data_url(image_path)},
                ],
            }
        ],
        text_format=PackageExtraction,
    )
    extraction = response.output_parsed
    if extraction is None:
        raise RuntimeError("The model did not return a structured package extraction.")

    context = "\n".join(f"{fact.nutrient}: {fact.value}" for fact in extraction.nutrition_facts)
    evaluations = [
        _evaluate_claim(
            claim.claim,
            claim.visible_evidence,
            context,
            extraction.ingredients,
            extraction.ingredient_list_complete,
            retriever,
            api_client,
            model,
        )
        for claim in extraction.claims
    ]
    claims = [evaluation[0] for evaluation in evaluations]
    classifications = _unique_classifications(
        classification for _, items in evaluations for classification in items
    )

    return AnalysisResult(
        nutrition_facts=extraction.nutrition_facts,
        ingredients=extraction.ingredients,
        ingredient_list_complete=extraction.ingredient_list_complete,
        claims=claims,
        regulatory_classifications=classifications,
        marketing_gap_score=marketing_gap_score(claim.verdict for claim in claims),
    )


def _evaluate_claim(
    claim: str,
    visible_evidence: list[str],
    context: str,
    ingredients: list[str],
    ingredient_list_complete: bool,
    retriever: FssaiRuleRetriever,
    client: OpenAI,
    model: str,
) -> tuple[ClaimAssessment, list[RegulatoryClassification]]:
    ingredient_list_check = check_ingredient_list(claim, ingredients, ingredient_list_complete)
    retrieved = retriever.retrieve(claim, context)
    if not retrieved:
        return (
            ClaimAssessment(
                claim=claim,
                visible_evidence=visible_evidence,
                verdict=Verdict.INSUFFICIENT_INFORMATION,
                rationale="No relevant FSSAI rule was retrieved from the local document collection.",
                applicable_rule=None,
                fssai_evidence=[],
                ingredient_list_check=ingredient_list_check,
            ),
            [],
        )

    response = client.responses.parse(
        model=model,
        instructions=EVALUATION_PROMPT,
        input=_evaluation_input(claim, visible_evidence, context, retrieved),
        text_format=ClaimDecision,
    )
    decision = response.output_parsed
    if decision is None:
        raise RuntimeError("The model did not return a structured claim decision.")

    selected = _selected_evidence(decision.evidence_indexes, retrieved)
    if not selected:
        return (
            ClaimAssessment(
                claim=claim,
                visible_evidence=visible_evidence,
                verdict=Verdict.INSUFFICIENT_INFORMATION,
                rationale="No retrieved FSSAI evidence was selected for this claim.",
                applicable_rule=None,
                fssai_evidence=[],
                ingredient_list_check=ingredient_list_check,
            ),
            [],
        )
    assessment = ClaimAssessment(
        claim=claim,
        visible_evidence=visible_evidence,
        verdict=decision.verdict,
        rationale=decision.rationale,
        applicable_rule=_source_label(selected[0]),
        fssai_evidence=selected,
        ingredient_list_check=ingredient_list_check,
    )
    classifications = []
    for item in decision.regulatory_classifications:
        classification_evidence = _selected_evidence(item.evidence_indexes, retrieved)
        if classification_evidence:
            classifications.append(
                RegulatoryClassification(
                    classification=item.classification,
                    visible_evidence=context.splitlines() or visible_evidence,
                    rationale=item.rationale,
                    applicable_rule=_source_label(classification_evidence[0]),
                    fssai_evidence=classification_evidence,
                )
            )
    return assessment, classifications


def _evaluation_input(
    claim: str, visible_evidence: list[str], context: str, evidence: list[RuleEvidence]
) -> list[dict[str, str]]:
    evidence_text = "\n\n".join(
        f"[{index}] Document: {item.document}; Source: {item.source}; Page: {item.page_number}; "
        f"Section: {item.section or 'Not detected'}\n{item.text}"
        for index, item in enumerate(evidence)
    )
    return [
        {
            "role": "user",
            "content": (
                f"Claim: {claim}\nVisible claim evidence: {visible_evidence}\n"
                f"Visible nutrition context:\n{context or 'None visible'}\n\n"
                f"Indexed retrieved FSSAI evidence:\n{evidence_text}"
            ),
        }
    ]


def _selected_evidence(indexes: list[int], evidence: list[RuleEvidence]) -> list[RuleEvidence]:
    selected: list[RuleEvidence] = []
    for index in indexes:
        if 0 <= index < len(evidence) and evidence[index] not in selected:
            selected.append(evidence[index])
    return selected


def _source_label(evidence: RuleEvidence) -> str:
    label = f"{evidence.document}, page {evidence.page_number}"
    return f"{label}, {evidence.section}" if evidence.section else label


def _unique_classifications(
    classifications: Iterable[RegulatoryClassification],
) -> list[RegulatoryClassification]:
    unique: list[RegulatoryClassification] = []
    seen: set[tuple[str, str]] = set()
    for classification in classifications:
        key = (classification.classification, classification.applicable_rule)
        if key not in seen:
            seen.add(key)
            unique.append(classification)
    return unique
