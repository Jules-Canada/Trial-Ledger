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
- [x] Build the schema validator (checks structure, enums, trial
      cross-references). Now `pipeline/validate.py` / `tl-validate` — see the
      Python-migration entry below (originally scripts/validate.mjs).
- [x] Drug #2 added: rociletinib (Clovis) — high-profile EGFR NSCLC failure.
      Exercises the discontinuation branch + a metric that collapsed on
      confirmation (ORR 60% unconfirmed → 28% confirmed). Schema held with NO
      changes — validated clean. Status: draft-unverified.
- [x] Drug #3 added: brepocitinib (Priovant/Pfizer) — non-oncology, TYK2/JAK1,
      MULTI-INDICATION with mixed outcomes (dermatomyositis Phase 3 win under
      FDA review; SLE Phase 2 failure; PsA/psoriasis Phase 2 wins). Endpoint-
      agnostic model held for ACR20/PASI/SRI-4/TIS. Status: draft-unverified.
- [x] Validator fix: allow unitless endpoints (unit "") — surfaced by TIS,
      the first composite-score endpoint.
- [x] Promoted indication + sponsor to first-class per-trial fields (schema doc
      + validator + types + backfilled all 3 records). Sponsor is per-trial
      because it transfers over a drug's life (brepocitinib: Pfizer → Priovant).
- [x] Drug #4 added: emraclidine (Cerevel/AbbVie) — CNS/schizophrenia, M4 PAM.
      Story: Phase 1b positive → Phase 2 EMPOWER-1/-2 failed to replicate (2024).
      Exercises array-sponsor (Cerevel → AbbVie acquisition) + a failed-but-not-
      formally-discontinued state. Status: draft-unverified.
- [x] Built CT.gov skeleton pre-fill (now `pipeline/prefill.py` / `tl-prefill`).
      Pulls authoritative phases/dates/sponsor/status/conditions for an NCT —
      erases the "date/NCT to confirm" error class from hand-built drafts.
- [x] Built agent-agnostic automated authoring (`tl-author "<drug>"`): LLM
      research+extract behind an `LlmProvider` base class, Claude adapter first,
      CT.gov skeleton merged over the LLM's guesses. Proven end-to-end.
- [x] **Migrated the whole pipeline TypeScript → Python** (maintainer is
      Python-native; the data/life-sci contributor pool skews Python). Frontend
      stays React+D3/TS. Now: `pipeline/*.py`, Pydantic schema in
      `pipeline/schema.py` as the single source of truth (validation + authoring
      contract + generated frontend types via `tl-gen-types`). Commands are the
      `tl-*` console scripts (pyproject.toml); npm covers only the frontend.
      Data records (`data/drugs/*.json`) unchanged; all 5 still validate.
- [ ] SHIFT (decided): move trust from human-verify-per-drug (can't scale to
      every drug in development) to provenance + automated confidence. Human
      review = optional spot-audit, not a gate. See docs/data-pipeline.md.
- [x] Drug #6 added: tofersen (Biogen/Ionis) — first drug authored through the
      Python pipeline. Neuro/rare (SOD1-ALS), antisense. Exercises a
      surrogate-biomarker accelerated approval: VALOR Phase 3 clinical primary
      (ALSFRS-R) MISSED (met=false) while biomarkers (CSF SOD1 -38%, plasma NfL
      -67%) hit (met=true) → accelerated approval on NfL. The endpoint-agnostic
      met? model captured "clinical miss, biomarker hit" cleanly.
- [x] Pipeline finding (from tofersen) + fix: a single registered study can span
      phases via parts (233AS101 = Phase 1/2 Parts A/B + Phase 3 Part C VALOR).
      The LLM split it into two trial objects sharing one NCT; merge_prefill then
      overwrote the Phase 1/2 part's phases to the registry's whole-study Phase 3,
      contradicting its own efficacy rows. Fixed: merge_prefill now keeps the
      LLM's phases on a registry mismatch and warns on duplicate NCTs. Open: a
      cleaner model for multi-part registered studies (one trial spanning phases
      vs. N part-objects) — decide before freezing the trial schema.
- [x] Model-agnostic authoring + cost accounting. Model is selectable
      (`--model` / `$LLM_MODEL`, default claude-opus-4-8); per-run token/cost is
      printed and model-aware. `tl-compare` authors a drug across models (default
      Opus vs Sonnet) into `_compare/` for high- vs low-cost output comparison.
- [x] First tl-compare run (sotorasib, Opus vs Sonnet) — findings:
      (1) Opus authored a MUCH richer record than the hand-curated reference
      (5 trials / 20 efficacy incl. the whole colorectal program vs 2 / 7) —
      automated authoring is more exhaustive; open question is per-figure
      accuracy vs breadth. (2) Surfaced + fixed two robustness bugs: research
      pause_turn resume didn't pass the code-execution container id (chatty
      models like Sonnet paused and 400'd; Opus finished in one turn and never
      hit it), and the phase guard misfired on "Phase 1" vs "1" formatting.
      Next: re-run Sonnet to confirm the container fix; judge quality (compare
      still reports shape + cost, not correctness).
- [x] Research-query provenance. The Claude adapter persists every server-side
      web_search/web_fetch it ran; `tl-author` writes `data/drugs/<id>.research.txt`
      (and `tl-compare` a per-model sidecar in `_compare/`). Makes the automated
      evidence-gathering auditable + reproducible, matching the per-datapoint
      provenance ethos. (Chatty models like Sonnet also make this a useful
      efficiency signal — 68 queries vs Opus's ~4 for the same drug.)
- [ ] Add per-record confidence tiers to the validator (source_type -> tier;
      provenance report: primary-evidence vs topline coverage per record).
- [ ] Backfill exact skeleton fields into the 4 drafts via prefill (optional).
- [ ] Create a blank record template + curation checklist.
- [ ] CT.gov trial DISCOVERY by intervention name (find a drug's NCTs, not just
      fetch known ones) — the next automation after confidence tiers.

## Schema findings from brepocitinib (need a decision before freezing)
1. **Indication must be first-class.** A multi-indication drug's trials and
   efficacy each belong to a *disease*; today `indication` is only a drug-level
   array. Added `indication` on trials as an additive stopgap; needs a proper
   schema + validator update (and it reshapes the view — the "signal" story is
   per-indication, e.g. small-multiples by disease).
2. **Discontinuation should be per-program, not drug-level.** Brepocitinib's SLE
   program was halted while dermatomyositis advances to registration — the
   top-level `discontinuation` field can't express "one indication dead, drug
   alive." (Only one case so far; don't over-model yet.)
3. **Third lifecycle state now present:** under-review (brepocitinib, PDUFA
   Q3 2026) alongside approved (sotorasib) and discontinued (rociletinib).
4. **Timeline enum lacks corporate events.** Emraclidine's Cerevel→AbbVie
   acquisition (Aug 2024) has no event type — captured via per-trial sponsor
   arrays instead. Add an `acquisition`/`corporate` event type only if the story
   needs it on the timeline (one case so far; deferred).
5. **Fourth lifecycle nuance:** failed-but-not-formally-discontinued
   (emraclidine schizophrenia — Phase 2 missed, AbbVie 'evaluating'; AD-psychosis
   Phase 1 still ongoing). `discontinuation: null` holds, but "in limbo" isn't
   explicitly modeled.

## Frontend generality (deferred until more drugs exist)
- The single-drug view is currently sotorasib-shaped: hardcoded per-drug
  NARRATIVE, assumes exactly 2 trials both with efficacy. rociletinib breaks
  it (terminated trial with no readout; 3 ORR-variant rows). Generalizing the
  view IS the real M4 work — drug #2 is the test case. Also pending: M4b
  interaction, M4c deploy to a public URL.
