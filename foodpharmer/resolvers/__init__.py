"""Verdict resolvers — deterministic Python logic per :class:`ClaimType`.

Every resolver takes a normalized claim plus the evidence gathered for it and
returns ``(Verdict, reason, Computation | None)``. All arithmetic lives here.
"""

from .base import resolve_claim

__all__ = ["resolve_claim"]
