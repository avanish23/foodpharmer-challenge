"""Evidence sources — packaging, FSSAI, and stubs for future data sources.

Each source implements the :class:`~foodpharmer.evidence.base.EvidenceSource`
Protocol. The dispatcher in :mod:`foodpharmer.evidence.base` walks a list of
sources in order and asks the first one that ``can_fulfill`` a requirement to
produce a :class:`GatheredEvidence`. A requirement that no source can fulfill
is never dropped — it is recorded as UNAVAILABLE with source ``"none"``.
"""

from .base import EvidenceSource, gather_all
from .comparator import ComparatorProductSource
from .fssai import FssaiRegulationSource
from .market import MarketDataSource
from .packaging import PackagingSource

__all__ = [
    "ComparatorProductSource",
    "EvidenceSource",
    "FssaiRegulationSource",
    "MarketDataSource",
    "PackagingSource",
    "gather_all",
]
