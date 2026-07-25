"""Claude adapter — the ONLY module that imports the Anthropic SDK.

Everything vendor-specific (server-side web tools, JSON extraction) is contained
here behind the vendor-neutral LlmProvider interface. Default model per the
claude-api guidance: claude-opus-4-8 with adaptive thinking.

Note on structured output: grammar-based structured outputs (messages.parse /
output_config json_schema) can't be used here — the compiled grammar for a
schema as nested as DrugRecord exceeds the API's size limit. Instead we embed
the schema in the prompt and validate the reply with Pydantic (see extract()).
"""

from __future__ import annotations

import copy
import json
import sys
from typing import Any, Optional

import anthropic
from pydantic import ValidationError

from pipeline.llm.provider import LlmProvider, LlmResult, T

# Non-structural JSON Schema keywords — dropped to keep the schema we embed in
# the prompt compact and readable (Pydantic still enforces these on the result).
_DROP_KEYS = {
    "title", "default", "minItems", "maxItems", "minLength", "maxLength",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "pattern",
    "format", "description",
}

# Properties the LLM should NOT generate: hand-curation extras
# (comparable/definition/confirmed) are added by curators, and _verification is
# stamped by author.py after generation.
_DROP_PROPS = {"_verification", "comparable", "definition", "confirmed"}


def _prompt_schema(schema: dict) -> dict:
    """Turn the full Pydantic JSON Schema into a compact schema to embed in the
    authoring prompt: inline $defs/$ref, strip non-structural keywords, and drop
    authoring-irrelevant props. Enums are kept — they tell the model the valid
    values (e.g. source_type). Grammar-based structured output is NOT used here:
    the compiled grammar for a schema this nested exceeds the API's size limit,
    so we prompt for JSON and validate the result with Pydantic instead."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return resolve(copy.deepcopy(defs[name]))
            out: dict = {}
            for k, v in node.items():
                if k in _DROP_KEYS:
                    continue
                if k == "properties":
                    v = {p: pv for p, pv in v.items() if p not in _DROP_PROPS}
                if k == "required":
                    v = [p for p in v if p not in _DROP_PROPS]
                out[k] = resolve(v)
            return out
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve({k: v for k, v in schema.items() if k != "$defs"})


def _extract_json(text: str) -> str:
    """Pull the JSON object out of a model reply, tolerating ```json fences or
    incidental prose around it."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip()
    start, end = t.find("{"), t.rfind("}")
    return t[start : end + 1] if start != -1 and end != -1 else t


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
        # Prompt-embedded JSON, not grammar-based structured output: the compiled
        # grammar for a schema as nested as DrugRecord exceeds the API's size
        # limit. We hand the model the schema and validate its reply with
        # Pydantic, with one corrective retry that feeds the validation error
        # back. output_model is still the single source of truth for the shape.
        schema = _prompt_schema(output_model.model_json_schema())
        instruction = (
            f"{prompt}\n\n"
            "Return ONLY a single JSON object that conforms to this JSON Schema. "
            "No prose, no markdown fences. Include every required property; use "
            "null (not omission) where a nullable value is unknown.\n\n"
            f"JSON Schema:\n{json.dumps(schema)}"
        )
        messages: list = [{"role": "user", "content": instruction}]
        base: dict = {"model": MODEL, "max_tokens": _MAX_TOKENS, "thinking": {"type": "adaptive"}}
        if system:
            base["system"] = system

        last_err: Optional[Exception] = None
        for attempt in range(2):
            response = self.client.messages.create(messages=messages, **base)
            raw = _text_of(response)
            js = _extract_json(raw)
            try:
                data: T = output_model.model_validate_json(js)
                return LlmResult(data=data, raw=js, provider=self.name, model=MODEL)
            except ValidationError as e:
                last_err = e
                if attempt == 0:
                    print("[extract] validation failed, retrying with error feedback", file=sys.stderr)
                    messages += [
                        {"role": "assistant", "content": raw},
                        {"role": "user", "content": (
                            f"That JSON failed schema validation:\n{e}\n\n"
                            "Return a corrected JSON object only.")},
                    ]
        raise RuntimeError(f"extract: response failed validation after retry: {last_err}")

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
