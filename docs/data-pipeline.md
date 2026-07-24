# Data Pipeline

How drug records get built, trusted, and validated — designed to scale toward
"every drug in development", where per-drug human verification is NOT feasible.

## Trust model: provenance, not human sign-off
Publishing is NOT gated on a human verifying every figure — that cannot scale
to thousands of drugs. Trust comes instead from **traceable provenance +
automated checks**:
- every data point carries a `source` + `source_type` (see drug-schema.md);
- `source_type` implies a **confidence tier** (primary evidence — journal /
  registry / FDA — outranks topline press releases / abstracts);
- the validator enforces structure; a provenance report summarizes coverage;
- the UI surfaces provenance so the reader audits credibility themselves.

Human review is an **optional spot-audit** (e.g. flagship drugs), never the
gate. Confidence is *expressed and traceable*, not *asserted by a human stamp*.

## Artifact
- one JSON per drug: `data/drugs/<id>.json`, conforms to drug-schema.md, in git.
- expansive capture: press releases / abstracts are included and flagged by
  `source_type`, never excluded (see the capture-expansive principle).

## Stages: gather → author → publish
1. **Gather (increasingly automated)**
   - Skeleton: `npm run prefill NCT03600883 …` (scripts/ctgov-prefill.mjs) pulls
     authoritative registry fields — phases, dates, sponsor, status, conditions,
     enrollment. This replaces hand-entering *and* hand-verifying the skeleton
     (the exact fields that were "to confirm" in our first drafts).
   - Efficacy / timeline: curated from journals / PR / FDA, each with a
     `source_type`. The registry does not carry topline efficacy.
2. **Author**
   - Fill the record from prefill stubs + curated efficacy. Set confidence via
     `source_type`, not a human stamp.
3. **Publish**
   - `npm run validate` must pass (structure + provenance). Commit. No human
     sign-off required; provenance travels with the data.

## What automation is authoritative for — and what it isn't
- CT.gov prefill: authoritative for the **skeleton** (identity, phases, dates,
  sponsor, status, enrollment). NOT for efficacy.
- Efficacy stays the judgment layer — **sourced and tiered, not human-verified
  per figure**. When sources disagree, keep both and note it.

## Tooling
- `scripts/validate.mjs` (`npm run validate`) — structure checks; provenance
  report is the next addition.
- `pipeline/ctgov-prefill.ts` (`npm run prefill <NCT…>`) — registry skeleton
  pre-fill CLI; shares `pipeline/ctgov.ts` with the authoring orchestrator, which
  merges the registry skeleton over the LLM's trial guesses automatically.
- Next: derive per-record **confidence tiers** from `source_type`; then CT.gov
  trial *discovery* by intervention name (find a drug's NCTs, not just fetch
  known ones).

## Secrets (ANTHROPIC_API_KEY)
- The key is used ONLY by the offline authoring CLI (pipeline/), never by the
  browser app (src/). The deployed static site never calls the API at runtime,
  so the key never goes to the host or the client bundle. **Never** prefix it
  with `VITE_` — Vite inlines those into public client JS.
- Provide it at runtime, never in git (`.env*` is gitignored; `.env.example` is
  the tracked template). Options, most to least secure:
  - macOS Keychain: `security add-generic-password -a "$USER" -s ANTHROPIC_API_KEY -w`
    once, then `ANTHROPIC_API_KEY=$(security find-generic-password -s ANTHROPIC_API_KEY -w) npm run author "<drug>"`.
  - `.env.local` (gitignored): copy from `.env.example`; `npm run author` auto-loads it.
  - Ephemeral shell export for the session.

## Status
- 4 drugs; schema stable (additive-only changes across all four).
- Trust model shifting from human-verify-per-drug → provenance + automated
  confidence.
