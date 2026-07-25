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

from pipeline.llm.provider import LlmProvider, LlmResult, T, Usage

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


DEFAULT_MODEL = "claude-opus-4-8"
# Proven working tool versions (see the prior TypeScript pipeline run). Claude
# drives these server-side, batching queries via programmatic tool calling.
_WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]
_MAX_TOKENS = 16000
# Extraction needs headroom for adaptive thinking on a large research digest
# PLUS the full JSON record; too small a cap yields an empty (all-thinking) reply.
_EXTRACT_MAX_TOKENS = 32000
_MAX_RESEARCH_TURNS = 6

# Pricing in USD per 1M tokens (input, output) — see the claude-api model table.
# Cache read/write are derived (0.1x / 1.25x of input). Used only for an
# end-of-run cost ESTIMATE; web_fetch isn't billed per call.
_PRICES = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}
_WEB_SEARCH_USD = 0.01  # ~$10 per 1000 searches


def _text_of(message) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


class ClaudeProvider(LlmProvider):
    name = "claude"

    def __init__(
        self,
        client: Optional[anthropic.Anthropic] = None,
        model: Optional[str] = None,
    ) -> None:
        # Anthropic() resolves ANTHROPIC_API_KEY from the environment.
        self.client = client or anthropic.Anthropic()
        self.model = model or DEFAULT_MODEL
        self.usage = Usage()
        # Auditable trail of every server-side web query/fetch the model ran,
        # persisted per record (see author.py) so the evidence-gathering is
        # reproducible — in keeping with the project's provenance ethos.
        self.research_log: list[str] = []

    def _record(self, response) -> None:
        """Fold one API response's usage into the running tally."""
        u = getattr(response, "usage", None)
        if u is None:
            return
        st = getattr(u, "server_tool_use", None)
        self.usage.add(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            web_searches=(getattr(st, "web_search_requests", 0) or 0) if st else 0,
        )

    def cost_usd(self) -> float:
        """Estimated USD cost of this run from the accumulated usage.
        Returns 0.0 for a model with no pricing entry (unknown model)."""
        price = _PRICES.get(self.model)
        if not price:
            return 0.0
        inp, outp = price
        u = self.usage
        token_cost = (
            u.input_tokens * inp
            + u.output_tokens * outp
            + u.cache_read_tokens * inp * 0.1
            + u.cache_write_tokens * inp * 1.25
        ) / 1_000_000
        return token_cost + u.web_searches * _WEB_SEARCH_USD

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
        # Generous output budget: a full record is ~6k tokens, and adaptive
        # thinking on a large digest can consume a lot before any text is emitted
        # — too small a cap yields an EMPTY response (all budget spent thinking).
        base: dict = {"model": self.model, "max_tokens": _EXTRACT_MAX_TOKENS, "thinking": {"type": "adaptive"}}
        if system:
            base["system"] = system

        last_err: Optional[Exception] = None
        for attempt in range(2):
            # Stream to avoid the SDK's non-streaming >10-min guard: a big digest
            # + 32k budget can run long, and a non-streamed call aborts AFTER
            # spending the tokens. get_final_message() gives the same Message.
            with self.client.messages.stream(messages=messages, **base) as stream:
                response = stream.get_final_message()
            self._record(response)
            raw = _text_of(response)
            stop = getattr(response, "stop_reason", None)
            if not raw:
                # Empty text — usually max_tokens hit during thinking. A same-size
                # retry won't help; report the real cause, not a JSON-parse error.
                last_err = RuntimeError(f"empty response (stop_reason={stop})")
                print(f"[extract] empty response (stop_reason={stop})", file=sys.stderr)
                continue
            try:
                data: T = output_model.model_validate_json(_extract_json(raw))
                return LlmResult(data=data, raw=raw, provider=self.name, model=self.model)
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
        raise RuntimeError(f"extract: failed after retry: {last_err}")

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
        # Claude drives the web tools from a code-execution container; when a turn
        # pauses with pending tool uses, the resume MUST reference that container
        # id or the API 400s ("container_id is required ..."). Chattier models
        # (e.g. Sonnet) hit this path where a one-shot model (Opus) may not.
        container: Optional[str] = None
        for _ in range(_MAX_RESEARCH_TURNS):
            params: dict = {
                "model": self.model,
                "max_tokens": _MAX_TOKENS,
                "thinking": {"type": "adaptive"},
                "tools": _WEB_TOOLS,
                "messages": messages,
            }
            if container:
                params["container"] = container
            # Stream: research turns run server-side web tools and can exceed the
            # non-streaming 10-min ceiling (the failure that wasted spend before).
            with self.client.messages.stream(**params) as stream:
                message = stream.get_final_message()
            self._record(message)
            self._log_web_tools(message)
            c = getattr(message, "container", None)
            if c is not None:
                container = getattr(c, "id", None) or container
            if message.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": message.content})
                continue
            return _text_of(message)
        raise RuntimeError("Claude research: exceeded max web-tool iterations")

    def _log_web_tools(self, message) -> None:
        """Print AND persist the model-generated web queries (server_tool_use
        blocks) so the research step is auditable and reproducible. The
        code-execution wrapper is printed but kept out of the saved log; only the
        actual web_search/web_fetch calls are recorded."""
        for b in message.content:
            if getattr(b, "type", None) == "server_tool_use":
                inp = b.input or {}
                arg = inp.get("query") or inp.get("url") or str(inp)
                print(f"[research]   {b.name}: {arg}", file=sys.stderr)
                if b.name in ("web_search", "web_fetch"):
                    self.research_log.append(f"{b.name}: {arg}")
