# Trial-Ledger

Trace a drug from first-in-human to launch (or failure), and watch its efficacy
signal evolve by phase. Public data only.

An interactive, editorial visualization of the clinical-development journey. The
atomic unit is a **single drug**; every view aggregates drug records. The first
view — **"The Signal Ledger"** — puts a drug's timeline next to how its efficacy
signal holds up as the evidence gets more rigorous (single-arm → randomized).

> Status: early work in progress. 4 drugs, 3 therapeutic areas, 3 lifecycle
> states (approved / discontinued / under-review).

## Two toolchains

Trial-Ledger is a **Python data pipeline + TypeScript frontend** — the common
"Python for data, TS for the web app" split.

- **Frontend** (`src/`) — React + D3, Node 20+ (developed on Node 26).
- **Pipeline** (`pipeline/`) — Python 3.11+. Authors and validates the drug
  records, and generates the frontend's TypeScript types from the canonical
  schema. Python owns the schema; the TS follows.

## Quick start

**Frontend (no API key needed):** the drug data is committed JSON, the site is static.

```sh
npm install
npm run dev        # open the Signal Ledger locally
npm run build      # type-check + static build
```

**Pipeline (Python):**

```sh
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .          # installs the tl-* commands
tl-validate              # check every data/drugs/*.json against the schema
```

## What's where

| Path | What |
|---|---|
| `src/` | React + D3 frontend (the Signal Ledger view) |
| `src/types.generated.ts` | TS types generated from the schema — do not edit |
| `data/drugs/*.json` | One curated record per drug (the source of truth) |
| `data/drugs/*.research.txt` | Per-drug web-query trail from automated authoring (provenance) |
| `data/drug-record.schema.json` | JSON Schema, emitted from `pipeline/schema.py` |
| `pipeline/` | Offline Python pipeline (schema, validate, CT.gov prefill, LLM authoring) |
| `pipeline/schema.py` | **Canonical drug-record schema** (Pydantic) — single source of truth |
| `docs/` | Schema, data pipeline, and design specs |

Start with `docs/drug-schema.md` (the data model) and
`docs/design/single-drug-view.md` (the visual).

## Commands

| Command | Needs key? | Does |
|---|---|---|
| `npm run dev` / `build` | no | run / build the frontend |
| `tl-validate` | no | validate all drug records against the schema |
| `tl-prefill NCT…` | no | fetch authoritative trial skeleton from ClinicalTrials.gov |
| `tl-gen-types` | no | regenerate `src/types.generated.ts` + the JSON Schema |
| `tl-author "<drug>"` | **yes** | auto-draft a drug record via an LLM |
| `tl-compare "<drug>"` | **yes** | author the same drug across models; compare cost + output |

(Each `tl-*` command is also runnable as `python -m pipeline.<module>`.)

**Model selection.** The authoring model is configurable — `tl-author --model
claude-sonnet-4-6 "<drug>"`, or set `$LLM_MODEL` (default `claude-opus-4-8`).
Each run prints its token usage and estimated cost. `tl-compare` runs a drug
through several models at once (default Opus vs Sonnet) into a `_compare/`
scratch dir so you can diff high- vs low-cost output.

## The authoring pipeline (needs your own key)

`tl-author "<drug>"` drafts a record: an LLM researches + extracts the judgment
layer (efficacy, timeline), and trial skeleton fields (phases, dates, sponsor,
status) are merged authoritatively from ClinicalTrials.gov. It's
**agent-agnostic** — Claude is the first provider behind an `LlmProvider` base
class (`LLM_PROVIDER` selects). See `docs/design/authoring-pipeline.md`.

Provide `ANTHROPIC_API_KEY` via `.env.local` (copy `.env.example`) — it's
gitignored and loaded automatically. The key is used **only** by this offline
CLI, never by the browser app, and the deployed site never needs it.

**Trust is provenance-based, not human sign-off** (which can't scale to every
drug in development): every data point carries a `source` + `source_type`, and
the validator is the gate. See `docs/data-pipeline.md`.

## Deploy

Static build (`npm run build` → `dist/`) deploys to Vercel or Netlify with zero
config. No secrets in the deployment — the site is client-side only.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Most contributions need no API key.
