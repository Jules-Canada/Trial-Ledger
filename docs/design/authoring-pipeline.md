# Automated Authoring Pipeline — Design

Turns the drug-record authoring step (today: Claude-in-a-chat, one drug at a
time) into a **programmatic, batchable** process. This is the real scaling move
— per docs/data-pipeline.md the deterministic tools (validator, CT.gov prefill)
already scale; the LLM authoring step did not.

The pipeline is **Python** (`pipeline/*.py`); the frontend is TypeScript. The
canonical record schema lives in `pipeline/schema.py` (Pydantic) and drives
validation, the authoring output contract, and the generated frontend types.

## Constraint: agent-agnostic
Start on the Claude API, but do **not** lock the pipeline to one vendor. The
orchestrator depends only on a provider **base class** (`pipeline/llm/provider.py`).
Vendor specifics — Anthropic structured outputs, Claude server-side web search —
live inside an adapter (`pipeline/llm/claude.py`). A second provider is a new
subclass, no orchestrator change. Provider is selected at runtime via
`LLM_PROVIDER` (default `claude`).

## The interface (vendor-neutral)
```python
class LlmProvider(ABC):
    name: str
    model: str
    def extract(*, prompt, output_model, system=None) -> LlmResult[T]: ...   # required
    def research(*, brief, output_model, system=None) -> LlmResult[T]: ...   # default = extract-only
```
- **`extract`** — pure structured extraction: text in, schema-valid Pydantic
  instance out. Every provider must implement it. The prompt and the target
  **Pydantic model are vendor-neutral**; the adapter maps them to that vendor's
  structured-output mechanism (Claude: `messages.parse(output_format=...)`).
- **`research`** — a provider with native web capability (Claude's server-side
  `web_search`/`web_fetch`) gathers its own sources, then extracts. The base
  class ships a default that simply extracts from the brief alone, so providers
  without web tools need only implement `extract`.

## Flow (gather → author → publish, automated)
```
drug name ──▶ [research → sourced digest] ──▶ [extract → schema-valid DrugRecord]
          ──▶ merge CT.gov prefill skeleton (authoritative dates/phases/sponsor)
          ──▶ stamp extractor provenance (provider+model, draft-unverified)
          ──▶ write data/drugs/<id>.json ──▶ tl-validate
```
No human gate — trust is provenance + automated checks (see the trust model in
docs/data-pipeline.md). The record records *which model authored it*, and every
data point keeps its `source_type` confidence signal.

## Claude adapter specifics (claude-opus-4-8)
- `extract`: `messages.parse(output_format=DrugRecord)` with adaptive thinking.
  The Pydantic model both constrains generation and validates the response —
  one source of truth. Structured outputs guarantee schema-valid JSON.
- `research`: a `web_search_20260209` + `web_fetch_20260209` loop produces a
  sourced digest (queries logged as `[research]` lines for auditability), then
  reuses `extract` on that digest — so the vendor-neutral extraction path is the
  single source of truth for the record shape.

## Boundaries (what stays deterministic, not LLM)
- **Skeleton** (phases, dates, sponsor, status) comes from CT.gov prefill and
  overrides the LLM's guesses — the registry is authoritative there
  (`merge_prefill` in `pipeline/author.py`, using `pipeline/ctgov.py`).
- **Validation** is the deterministic gate (`tl-validate` → `pipeline/schema.py`).
- The LLM's job is the judgment layer: efficacy, timeline narrative, endpoints.

## Status / next
- Built: provider base class, Claude adapter, orchestrator CLI (`tl-author
  "<drug>"`). Needs `ANTHROPIC_API_KEY` to run live.
- Built: CT.gov prefill merged into the orchestrator (`pipeline/ctgov.py`) —
  every trial with a real NCT gets phases/dates/sponsor/status overwritten from
  the registry; the LLM keeps id/indication/note/name.
- Built: schema → frontend type generation (`tl-gen-types`) keeps
  `src/types.generated.ts` in sync with `pipeline/schema.py`.
- TODO: batch mode (many drugs); per-record confidence tiers in the validator;
  second provider adapter to exercise the abstraction.
