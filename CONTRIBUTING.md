# Contributing to Trial-Ledger

Thanks for your interest! Most contributions need **no API key** — the drug
records are committed JSON and the site is static.

## Setup

```sh
npm install     # also installs the git pre-commit hook (husky)
npm run dev
```

## Ways to contribute

- **Frontend / design** — work in `src/`. No key needed.
- **Data — fix or add a drug record** — edit `data/drugs/*.json`. No key needed
  to hand-curate; a key is only needed if you use the automated authoring CLI.
- **Pipeline / tooling** — `pipeline/`, `scripts/`.

## The data model

The drug is the atomic unit. Read `docs/drug-schema.md`. Key rules:
- **Endpoint-agnostic efficacy** — store whatever endpoint each trial reported
  (ORR, PFS, ACR20, PANSS, …), with `role` and per-endpoint `met?`.
- **Trials are first-class** — a trial can span phases and belongs to one
  indication and one sponsor (sponsorship can transfer over time).
- **Timeline is dated events**, not a fixed sequence (accelerated approval can
  precede the confirmatory Phase 3 readout).
- **Provenance, not human sign-off** — every data point needs a `source` +
  `source_type`. Capture expansively (press releases included) and flag the
  type; don't drop data. See `docs/data-pipeline.md`.

## Adding a drug

1. **Automated (needs a key):** `npm run author "<drug>"` drafts
   `data/drugs/<id>.json`. Or **manual:** copy an existing record and edit.
2. **Prefill skeletons:** `npm run prefill NCT…` for authoritative trial
   fields from ClinicalTrials.gov.
3. **Validate:** `npm run validate` must pass (structure, enums, trial
   cross-references).
4. Open a PR. New records land as `draft-unverified` — that's expected.

## Secrets — never commit a key

- `ANTHROPIC_API_KEY` goes in `.env.local` (gitignored). Never hardcode it,
  never prefix it with `VITE_` (that would ship it in public browser JS).
- A **gitleaks** pre-commit hook scans staged changes. Install the scanner so
  it runs locally:
  - macOS: `brew install gitleaks`
  - other: https://github.com/gitleaks/gitleaks#installing
- Maintainers: enable **GitHub push protection** (repo Settings → Code
  security) as the server-side backstop.

## Before you push

- `npm run validate` passes
- `npm run build` type-checks and builds
- No secrets in the diff
