# Trial-Ledger

Trace a drug from first-in-human to launch (or failure), and watch its efficacy
signal evolve by phase. Public data only.

An interactive, editorial visualization of the clinical-development journey. The
atomic unit is a **single drug**; every view aggregates drug records. The first
view — **"The Signal Ledger"** — puts a drug's timeline next to how its efficacy
signal holds up as the evidence gets more rigorous (single-arm → randomized).

> Status: early work in progress. 4 drugs, 3 therapeutic areas, 3 lifecycle
> states (approved / discontinued / under-review).

## Quick start (no API key needed)

Most work — the frontend and the curated drug records — needs **no API key**.
The drug data is committed JSON and the site is static.

```sh
npm install
npm run dev        # open the Signal Ledger locally
npm run validate   # check every data/drugs/*.json against the schema
```

Requires Node 20+ (developed on Node 26).

## What's where

| Path | What |
|---|---|
| `src/` | React + D3 frontend (the Signal Ledger view) |
| `data/drugs/*.json` | One curated record per drug (the source of truth) |
| `scripts/validate.mjs` | Dependency-free schema validator |
| `pipeline/` | Offline data pipeline (CT.gov prefill + LLM authoring) |
| `docs/` | Schema, data pipeline, and design specs |

Start with `docs/drug-schema.md` (the data model) and
`docs/design/single-drug-view.md` (the visual).

## Commands

| Command | Needs key? | Does |
|---|---|---|
| `npm run dev` / `build` | no | run / build the frontend |
| `npm run validate` | no | validate all drug records |
| `npm run prefill NCT…` | no | fetch authoritative trial skeleton from ClinicalTrials.gov |
| `npm run author "<drug>"` | **yes** | auto-draft a drug record via an LLM |

## The authoring pipeline (needs your own key)

`npm run author "<drug>"` drafts a record: an LLM researches + extracts the
judgment layer (efficacy, timeline), and trial skeleton fields (phases, dates,
sponsor, status) are merged authoritatively from ClinicalTrials.gov. It's
**agent-agnostic** — Claude is the first provider behind an `LlmProvider`
interface (`LLM_PROVIDER` selects). See `docs/design/authoring-pipeline.md`.

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
