# Roadmap / Open Questions

This file is expected to churn as the project progresses — kept separate
from CLAUDE.md for that reason.

## Build Order
1. Nail the schema (docs/drug-schema.md) and manually populate it for 1 drug end-to-end (idea → launch or discontinuation)
2. Build the single-drug trace view (a "life story" timeline of that one asset)
3. Repeat for a handful more drugs (5-10), reusing the schema
4. Only then build the aggregate views (pipeline shape, cross-drug efficacy evolution) on top

## Status
- [x] Scope decided: single drug as the functional unit, expand drug-by-drug
- [x] First drug picked: **sotorasib (Lumakras)** — clean modern approval,
      oncology (KRAS G12C NSCLC), full idea→launch arc, ClinicalTrials.gov-era
- [x] Efficacy is **endpoint-agnostic** — do NOT force one fixed metric; each
      drug/phase stores whatever endpoint it reported (resolved, was open)
- [x] Schema validated against sotorasib and revised (see docs/drug-schema.md)
- [x] Hand-enter the full sotorasib record against the revised schema
      (data/drugs/sotorasib.json — all fields sourced)
- [x] Confirm remaining sotorasib gaps: FIH date (Aug 2018), NDA filing
      (2020-12-16), Phase 3 median PFS (5.6mo) and ORR (28.1%) all captured
- [x] Human spot-check sotorasib efficacy figures vs cited sources
      (record status: verified, 2026-07-23)
- [x] Design pass on the single-drug timeline visual — "The Signal Ledger",
      desktop horizontal first (see docs/design/single-drug-view.md)
- [~] Build the single-drug view (M4): React + D3, renders sotorasib.json
      — static Signal Ledger renders; interaction + deploy still to do
- [ ] M4b: add interaction (hover endpoints/nodes → sources, notes, links).
      The shareable artifact is an interactive tool at a URL, NOT a screenshot.
- [ ] M4c: deploy to a real public URL (Vercel/Netlify). Core, not a nicety.
- [ ] Build lightweight data-prep workflow: manual curation first, ClinicalTrials.gov
      API pull to automate once schema is proven on a few drugs

## What sotorasib validation surfaced (schema-shaping)
- Phases are NOT always discrete: CodeBreaK 100 was one Phase 1/2 trial →
  trial is its own object, efficacy attaches to a trial not a phase boundary.
- Timeline is non-linear: accelerated approval (May 2021) preceded the
  confirmatory Phase 3 readout (Aug 2022) → model timeline as dated events.
- "met?" is per-endpoint, not per-phase: Phase 3 met PFS but missed OS →
  "primary endpoint met" is a derived rollup, not a stored boolean.
- Endpoint roles shift by phase (OS exploratory in P1/2, secondary in P3).

## Data creation pipeline (rebalanced focus — data was lagging the frontend)
- [x] Build the schema validator: scripts/validate.mjs, `npm run validate`
      (dependency-free; checks structure, enums, trial cross-references)
- [x] Drug #2 added: rociletinib (Clovis) — high-profile EGFR NSCLC failure.
      Exercises the discontinuation branch + a metric that collapsed on
      confirmation (ORR 60% unconfirmed → 28% confirmed). Schema held with NO
      changes — validated clean. Status: draft-unverified.
- [ ] Human spot-check rociletinib; confirm approx dates + TIGER-3 NCT
- [ ] Create a blank record template + curation checklist (make drug #3-5 fast)
- [ ] Add drugs #3-5 by hand, then reassess whether schema can freeze
- [ ] Only after ~5 drugs + frozen schema: consider CT.gov skeleton pre-fill

## Frontend generality (deferred until more drugs exist)
- The single-drug view is currently sotorasib-shaped: hardcoded per-drug
  NARRATIVE, assumes exactly 2 trials both with efficacy. rociletinib breaks
  it (terminated trial with no readout; 3 ORR-variant rows). Generalizing the
  view IS the real M4 work — drug #2 is the test case. Also pending: M4b
  interaction, M4c deploy to a public URL.
