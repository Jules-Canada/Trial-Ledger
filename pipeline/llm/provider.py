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
