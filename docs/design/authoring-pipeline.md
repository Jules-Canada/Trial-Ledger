# Automated Authoring Pipeline — Design

Turns the drug-record authoring step (today: Claude-in-a-chat, one drug at a
time) into a **programmatic, batchable** process. This is the real scaling move
— per docs/data-pipeline.md the deterministic tools (validator, CT.gov prefill)
already scale; the LLM authoring step did not.

## Constraint: agent-agnostic
Start on the Claude API, but do **not** lock the pipeline to one vendor. The
orchestrator depends only on a provider **interface** (`pipeline/llm/provider.ts`).
Vendor specifics — Anthropic structured outputs, Claude server-side web search —
live inside an adapter (`pipeline/llm/claude.ts`). A second provider is a new
adapter, no orchestrator change. Provider is selected at runtime via
`LLM_PROVIDER` (default `claude`).

## The interface (vendor-neutral)
```
LlmProvider {
  name, model
  extract<T>({ system?, prompt, schema }): { data, raw, provider, model }   // required
  research?<T>({ brief, schema, system? }): ...                             // optional
}
```
- **`extract`** — pure structured extraction: text in, schema-valid JSON out.
  Every provider must implement it. Prompts and the target **JSON Schema are
  vendor-neutral**; the adapter maps them to that vendor's structured-output
  mechanism (Claude: `output_config.format`).
- **`research`** — optional. A provider with native web capability (Claude's
  server-side `web_search`/`web_fetch`) gathers its own sources, then extracts.
  Providers without it omit `research`; the orchestrator falls back to a
  separate gather step feeding `extract`.

## Flow (gather → author → publish, automated)
```
drug name ──▶ [research? or gather] ──▶ [extract → schema-valid record]
          ──▶ merge CT.gov prefill skeleton (authoritative dates/phases/sponsor)
          ──▶ stamp extractor provenance (provider+model, draft-unverified)
          ──▶ write data/drugs/<id>.json ──▶ npm run validate
```
No human gate — trust is provenance + automated checks (see the trust model in
docs/data-pipeline.md). The record records *which model authored it*, and every
data point keeps its `source_type` confidence signal.

## Claude adapter specifics (claude-opus-4-8)
- `extract`: `messages.create` with `output_config.format` = the record JSON
  Schema, adaptive thinking. Structured outputs guarantee schema-valid JSON.
- `research`: a `web_search_20260209` + `web_fetch_20260209` loop produces a
  sourced digest, then reuses `extract` on that digest — so the vendor-neutral
  extraction path is the single source of truth for the record shape.

## Boundaries (what stays deterministic, not LLM)
- **Skeleton** (phases, dates, sponsor, status) comes from CT.gov prefill and
  should override the LLM's guesses — the registry is authoritative there.
- **Validation** is the deterministic gate (`npm run validate`), unchanged.
- The LLM's job is the judgment layer: efficacy, timeline narrative, endpoints.

## Status / next
- Scaffolded: provider interface, Claude adapter, orchestrator CLI (`npm run
  author "<drug>"`). Needs `ANTHROPIC_API_KEY` to run live.
- TODO: merge CT.gov prefill into the orchestrator (currently extract-only);
  batch mode (many drugs); per-record confidence tiers in the validator;
  second provider adapter to exercise the abstraction.
