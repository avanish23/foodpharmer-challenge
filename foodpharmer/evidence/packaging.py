"""Packaging evidence source — reads facts already in the extraction.

Handles the ``packaging``-hint requirements: nutrient values, the ingredient
list, and any percentage disclosures visible on the label. No external I/O.
"""

from __future__ import annotations

import re

from ..models import (
    EvidenceRequirement,
    EvidenceStatus,
    GatheredEvidence,
    PackageExtraction,
    RequirementType,
)


# Grab the first number in a fact string like "6.5 g per 100 g" -> 6.5, "g".
# Only whitelisted units are captured — otherwise words like "per" in
# "3.75 per 100 g" leak into the unit slot.
_KNOWN_UNITS = "g|mg|µg|mcg|kg|kcal|cal|kj|ml|l|iu|%"
_VALUE_UNIT_RE = re.compile(
    rf"([-+]?\d+(?:\.\d+)?)\s*({_KNOWN_UNITS})?\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


class PackagingSource:
    """Answers requirements that can be satisfied from the label itself."""

    source_id = "packaging"

    _handles = {
        RequirementType.NUTRIENT_VALUE,
        RequirementType.INGREDIENT_LIST,
        RequirementType.DECLARED_PERCENTAGE,
    }

    def can_fulfill(self, requirement: EvidenceRequirement) -> bool:
        return requirement.requirement_type in self._handles

    def fulfill(
        self,
        requirement: EvidenceRequirement,
        extraction: PackageExtraction,
    ) -> GatheredEvidence:
        if requirement.requirement_type is RequirementType.NUTRIENT_VALUE:
            return self._nutrient_value(requirement, extraction)
        if requirement.requirement_type is RequirementType.INGREDIENT_LIST:
            return self._ingredient_list(requirement, extraction)
        if requirement.requirement_type is RequirementType.DECLARED_PERCENTAGE:
            return self._declared_percentage(requirement, extraction)
        raise ValueError(f"PackagingSource cannot fulfill {requirement.requirement_type}.")

    # ------------------------------------------------------------------
    # Requirement handlers
    # ------------------------------------------------------------------

    def _nutrient_value(
        self, requirement: EvidenceRequirement, extraction: PackageExtraction
    ) -> GatheredEvidence:
        needle = _keyword_from_description(requirement.description)
        match = _match_nutrition_fact(extraction, needle)
        if match is None:
            return GatheredEvidence(
                requirement=requirement,
                status=EvidenceStatus.UNAVAILABLE,
                data=None,
                source=self.source_id,
                note=f"No nutrition fact matched '{needle}' on the label.",
            )
        value, unit = _split_value(match.value)
        # Some labels put the unit inside the nutrient name ("Dietary fiber (g)"
        # → value "3.75 per 100g"). Fall back to the nutrient string's unit
        # hint when the value doesn't carry one.
        if unit is None:
            unit = _unit_from_label(match.nutrient)
        return GatheredEvidence(
            requirement=requirement,
            status=EvidenceStatus.AVAILABLE,
            data={
                "nutrient": match.nutrient,
                "value_str": match.value,
                "value": value,
                "unit": unit,
            },
            source=self.source_id,
        )

    def _ingredient_list(
        self, requirement: EvidenceRequirement, extraction: PackageExtraction
    ) -> GatheredEvidence:
        if not extraction.ingredients:
            return GatheredEvidence(
                requirement=requirement,
                status=EvidenceStatus.UNAVAILABLE,
                data=None,
                source=self.source_id,
                note="No ingredient entries were extracted from the package.",
            )
        return GatheredEvidence(
            requirement=requirement,
            status=EvidenceStatus.AVAILABLE,
            data={
                "ingredients": list(extraction.ingredients),
                "complete": extraction.ingredient_list_complete,
            },
            source=self.source_id,
        )

    def _declared_percentage(
        self, requirement: EvidenceRequirement, extraction: PackageExtraction
    ) -> GatheredEvidence:
        needle = _keyword_from_description(requirement.description)
        haystack: list[str] = []
        haystack.extend(extraction.ingredients)
        for claim in extraction.claims:
            haystack.append(claim.claim)
            haystack.extend(claim.visible_evidence)
        for entry in haystack:
            if needle and needle.lower() in entry.lower():
                match = _PERCENT_RE.search(entry)
                if match:
                    return GatheredEvidence(
                        requirement=requirement,
                        status=EvidenceStatus.AVAILABLE,
                        data={"disclosure": entry, "percentage": float(match.group(1))},
                        source=self.source_id,
                    )
        return GatheredEvidence(
            requirement=requirement,
            status=EvidenceStatus.UNAVAILABLE,
            data=None,
            source=self.source_id,
            note=f"No percentage disclosure for '{needle}' was visible on the label.",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Fact:
    __slots__ = ("nutrient", "value")

    def __init__(self, nutrient: str, value: str) -> None:
        self.nutrient = nutrient
        self.value = value


def _match_nutrition_fact(extraction: PackageExtraction, needle: str) -> _Fact | None:
    if not needle:
        return None
    lowered = needle.lower()
    tokens = [tok for tok in re.findall(r"[a-z]+", lowered) if len(tok) > 2]
    for fact in extraction.nutrition_facts:
        label = fact.nutrient.lower()
        if lowered and lowered in label:
            return _Fact(fact.nutrient, fact.value)
        if any(token in label for token in tokens):
            return _Fact(fact.nutrient, fact.value)
    return None


_UNIT_HINT_RE = re.compile(rf"\((?P<unit>{_KNOWN_UNITS})\)", re.IGNORECASE)


def _unit_from_label(label: str) -> str | None:
    """Extract a parenthesized unit hint from a nutrient label, e.g. "Fibre (g)"."""

    match = _UNIT_HINT_RE.search(label)
    return match.group("unit").lower() if match else None


def _split_value(raw: str) -> tuple[float | None, str | None]:
    match = _VALUE_UNIT_RE.search(raw)
    if not match:
        return None, None
    try:
        value = float(match.group(1))
    except ValueError:
        return None, None
    unit = match.group(2)
    return value, unit.lower() if unit else None


def _keyword_from_description(description: str) -> str:
    """Pull the most-informative word from a requirement description.

    Descriptions are hand-written in :mod:`foodpharmer.requirements` and always
    contain the nutrient or ingredient name — this heuristic works for the
    canonical cases but is intentionally simple.
    """

    # Grab quoted phrases first ("dietary fibre").
    quoted = re.findall(r"'([^']+)'", description)
    if quoted:
        return quoted[0]
    # Otherwise the last meaningful noun-ish token.
    words = re.findall(r"[A-Za-z]+", description)
    stop = {
        "declared", "value", "of", "on", "the", "package", "product", "content",
        "matching", "with", "for", "and", "or", "an", "a", "in", "list",
        "ingredient", "ingredients", "label", "visible", "complete", "from",
        "confirming", "presence", "disclosure", "percentage", "criterion",
    }
    for word in reversed(words):
        if word.lower() not in stop:
            return word
    return words[-1] if words else ""
