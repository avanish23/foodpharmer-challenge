"""Deterministic scoring for FoodPharmer claim results."""

from collections.abc import Iterable
from enum import Enum


def marketing_gap_score(verdicts: Iterable[str | Enum]) -> float | None:
    """Return the V1 Marketing Gap Score, independent of any model response.

    Supported and not-supported claims are assessable. Insufficient-information
    claims are not assessable and therefore do not affect the percentage.
    """

    normalized = [
        item.value if isinstance(item, Enum) else item
        for item in verdicts
    ]
    assessable = [
        verdict
        for verdict in normalized
        if verdict in {"SUPPORTED", "NOT_SUPPORTED"}
    ]
    if not assessable:
        return None
    return (assessable.count("NOT_SUPPORTED") / len(assessable)) * 100
