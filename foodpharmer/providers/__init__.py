"""LLM providers — real OpenAI and offline fixture backends.

Both implement the same :class:`~foodpharmer.providers.base.LLMProvider`
Protocol so the pipeline is provider-agnostic. Tests use the fixture provider;
the demo CLI defaults to fixture mode and can switch to OpenAI when an API
key is present.
"""

from .base import LLMProvider
from .fixture_provider import FixtureProvider

__all__ = ["FixtureProvider", "LLMProvider"]
