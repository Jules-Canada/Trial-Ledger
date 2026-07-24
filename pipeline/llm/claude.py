"""Claude adapter — the ONLY module that imports the Anthropic SDK.

Everything vendor-specific (structured outputs, server-side web tools) is
contained here behind the vendor-neutral LlmProvider interface. Default model
per the claude-api guidance: claude-opus-4-8 with adaptive thinking.
"""

from __future__ import annotations

import sys
from typing import Optional

import anthropic

from pipeline.llm.provider import LlmProvider, LlmResult, T

MODEL = "claude-opus-4-8"
# Proven working tool versions (see the prior TypeScript pipeline run). Claude
# drives these server-side, batching queries via programmatic tool calling.
_WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]
_MAX_TOKENS = 16000
_MAX_RESEARCH_TURNS = 6


def _text_of(message) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


class ClaudeProvider(LlmProvider):
    name = "claude"
    model = MODEL

    def __init__(self, client: Optional[anthropic.Anthropic] = None) -> None:
        # Anthropic() resolves ANTHROPIC_API_KEY from the environment.
        self.client = client or anthropic.Anthropic()

    def extract(
        self,
        *,
        prompt: str,
        output_model: type[T],
        system: Optional[str] = None,
    ) -> LlmResult[T]:
        # messages.parse constrains generation to output_model's JSON Schema AND
        # validates the response into a typed instance — one source of truth.
        kwargs = dict(
            model=MODEL,
            max_tokens=_MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_format=output_model,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        response = self.client.messages.parse(**kwargs)
        data: T = response.parsed_output
        raw = _text_of(response) or data.model_dump_json()
        return LlmResult(data=data, raw=raw, provider=self.name, model=MODEL)

    def research(
        self,
        *,
        brief: str,
        output_model: type[T],
        system: Optional[str] = None,
    ) -> LlmResult[T]:
        # Phase 1: gather a sourced digest with Claude's server-side web tools.
        digest = self._gather(brief)
        # Phase 2: reuse the vendor-neutral extraction path on the digest, so the
        # record shape has a single source of truth.
        prompt = f"{brief}\n\n--- RESEARCH DIGEST (with sources) ---\n{digest}"
        return self.extract(prompt=prompt, output_model=output_model, system=system)

    def _gather(self, brief: str) -> str:
        messages = [
            {
                "role": "user",
                "content": (
                    "Research the following and produce a thorough, factual digest "
                    "with source URLs for every claim. Plain prose, not JSON.\n\n"
                    + brief
                ),
            }
        ]
        # Server-side tools run automatically; on pause_turn, re-send to resume.
        for _ in range(_MAX_RESEARCH_TURNS):
            message = self.client.messages.create(
                model=MODEL,
                max_tokens=_MAX_TOKENS,
                thinking={"type": "adaptive"},
                tools=_WEB_TOOLS,
                messages=messages,
            )
            self._log_web_tools(message)
            if message.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": message.content})
                continue
            return _text_of(message)
        raise RuntimeError("Claude research: exceeded max web-tool iterations")

    @staticmethod
    def _log_web_tools(message) -> None:
        """Surface model-generated web queries (server_tool_use blocks) so the
        research step is auditable."""
        for b in message.content:
            if getattr(b, "type", None) == "server_tool_use":
                inp = b.input or {}
                arg = inp.get("query") or inp.get("url") or str(inp)
                print(f"[research]   {b.name}: {arg}", file=sys.stderr)
