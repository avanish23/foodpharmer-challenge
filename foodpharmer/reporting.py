"""Human-readable rendering of a :class:`ClaimAnalysisResult`.

Kept separate from :mod:`foodpharmer.pipeline` so the JSON audit trail stays
untouched — this module only formats what the pipeline already produced.
"""

from __future__ import annotations

from .models import (
    ClaimAnalysisResult,
    ClaimResult,
    EvidenceStatus,
    GatheredEvidence,
    Verdict,
)


_VERDICT_GLYPH = {
    Verdict.SUBSTANTIATED: "✓",
    Verdict.CONTRADICTED: "✗",
    Verdict.UNSUBSTANTIATED: "?",
    Verdict.NON_FALSIFIABLE: "~",
}


def render_compact(result: ClaimAnalysisResult) -> str:
    """One-screen summary of the analysis — no giant FSSAI blobs."""

    lines: list[str] = []
    if result.image_path:
        lines.append(f"Image: {result.image_path}")
    lines.append("─" * 70)

    ext = result.extraction
    completeness = "complete" if ext.ingredient_list_complete else "incomplete"
    if ext.ingredients:
        lines.append(f"Ingredients ({completeness}): {', '.join(ext.ingredients)}")
    if ext.nutrition_facts:
        facts = "; ".join(f"{f.nutrient} {f.value}" for f in ext.nutrition_facts)
        lines.append(f"Nutrition: {facts}")
    lines.append("")

    if not result.claims:
        lines.append("No marketing claims extracted.")
        return "\n".join(lines)

    for index, claim in enumerate(result.claims, start=1):
        lines.extend(_render_claim(index, claim))
        lines.append("")

    verdicts = [c.verdict for c in result.claims]
    lines.append(_summary_line(verdicts))
    return "\n".join(lines).rstrip() + "\n"


def _render_claim(index: int, claim: ClaimResult) -> list[str]:
    glyph = _VERDICT_GLYPH.get(claim.verdict, "?")
    lines = [
        f'Claim {index}: "{claim.claim_text}"',
        f"  Type:    {claim.claim_type.value}",
        f"  Verdict: {glyph} {claim.verdict.value}",
        f"  Reason:  {_wrap(claim.reason, indent=11)}",
    ]
    if claim.computation is not None:
        comp = claim.computation
        result_str = f"{comp.result}" if comp.result is not None else "n/a"
        unit = f" {comp.unit}" if comp.unit else ""
        passed = "passed" if comp.passed else "did not pass"
        lines.append(
            f"  Compute: {comp.operation} → {result_str}{unit} ({passed})"
        )
    if claim.available_evidence:
        for entry in claim.available_evidence:
            lines.append(f"  {_render_evidence(entry)}")
    return lines


def _render_evidence(entry: GatheredEvidence) -> str:
    kind = entry.requirement.requirement_type.value
    if entry.status is EvidenceStatus.AVAILABLE:
        tag = f"✓ {kind} ({entry.source})"
        detail = _evidence_detail(entry)
        return f"{tag}: {detail}" if detail else tag
    note = f" — {entry.note}" if entry.note else ""
    return f"✗ {kind} unavailable ({entry.source}){note}"


def _evidence_detail(entry: GatheredEvidence) -> str:
    data = entry.data or {}
    if "nutrient" in data and "value" in data:
        unit = data.get("unit") or ""
        return f"{data['nutrient']} = {data['value']}{unit}"
    if "ingredients" in data:
        count = len(data["ingredients"])
        return f"{count} ingredient(s), {'complete' if data.get('complete') else 'incomplete'}"
    if "percentage" in data:
        return f"disclosed {data['percentage']}%"
    if "evidence" in data:
        hits = data["evidence"]
        if hits:
            first = hits[0]
            section = first.get("section") or "n/a"
            return f"{len(hits)} rule hit(s), first: {first.get('source')} p.{first.get('page_number')} §{section}"
        return "no rule hits"
    return ""


def _summary_line(verdicts: list[Verdict]) -> str:
    counts = {v: 0 for v in Verdict}
    for verdict in verdicts:
        counts[verdict] += 1
    parts = [f"{counts[v]} {v.value}" for v in Verdict if counts[v]]
    return "Summary: " + ", ".join(parts)


def _wrap(text: str, *, indent: int, width: int = 90) -> str:
    """Simple word-wrap for terminal readability."""

    words = text.split()
    lines: list[str] = []
    current = ""
    prefix = " " * indent
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    if not lines:
        return ""
    return lines[0] + "".join(f"\n{prefix}{line}" for line in lines[1:])
