"""Agent-agnostic LLM provider interface.

The authoring pipeline depends ONLY on this base class — never on a specific
vendor SDK. Claude is the first implementation (see claude.py); other providers
subclass `LlmProvider` with no change to the orchestrator. Select at runtime via
the LLM_PROVIDER env var. See docs/design/authoring-pipeline.md.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class LlmResult(Generic[T]):
    data: T
    raw: str
    provider: str
    model: str


@dataclass
class Usage:
    """Running tally of token/tool consumption across every API call in a run.
    Vendor-neutral counters; providers translate their own response shapes into
    add(). Cost is model-specific, so it's computed by the provider, not here."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    web_searches: int = 0

    def add(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        web_searches: int = 0,
    ) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_read_tokens += cache_read_tokens
        self.cache_write_tokens += cache_write_tokens
        self.web_searches += web_searches


class LlmProvider(ABC):
    #: Short provider id (e.g. "claude"), also used in the _verification stamp.
    name: str
    #: Concrete model identifier used for the run.
    model: str

    @abstractmethod
    def extract(
        self,
        *,
        prompt: str,
        output_model: type[T],
        system: Optional[str] = None,
    ) -> LlmResult[T]:
        """Extract a schema-valid `output_model` instance from `prompt`.

        Every provider implements this.
        """

    def research(
        self,
        *,
        brief: str,
        output_model: type[T],
        system: Optional[str] = None,
    ) -> LlmResult[T]:
        """Gather web sources for `brief`, then extract.

        Default implementation has no native web capability and simply extracts
        from the brief alone. Providers with server-side web tools (e.g. Claude)
        override this to gather a sourced digest first.
        """
        return self.extract(prompt=brief, output_model=output_model, system=system)
