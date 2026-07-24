# Data Pipeline

How drug records get built, verified, and validated. Complements
docs/data-sources.md (where data comes from) and docs/drug-schema.md (shape).

## Artifact
- One hand-authored JSON file per drug: `data/drugs/<drug-id>.json`.
- Conforms to docs/drug-schema.md. Versioned in git. The app reads these
  files directly — there is no live scraper at page load.
- Every data point carries `source` (link + `source_type`). Capture is
  expansive: press releases and abstracts are included, flagged by type,
  not excluded. (See drug-schema.md "Sources".)

## Build loop (per drug)
1. **Claude searches + drafts** — WebSearch/WebFetch across ClinicalTrials.gov,
   press releases/IR, journals, Drugs@FDA. Fills the JSON, attaching a source
   (link + source_type) to every data point. Flags conflicts and gaps.
2. **Human verifies** — spot-checks each efficacy figure against its linked
   source before the record is trusted. The per-point source link exists to
   make this ~10-second, not a re-research.
3. **Validate + commit** — run the schema validator (below); commit the JSON.

Claude-drafted numbers are NOT ground truth until step 2. Risks: transposed
digits, stale figures (e.g. sotorasib ORR 37% → 41% across readouts), or
confident statements absent from the source. A record stays marked
`draft-unverified` until a human clears it.

## Division of labor
- **Claude is good at:** finding trials, assembling the skeleton, pulling
  candidate efficacy figures fast, drafting valid JSON, surfacing conflicts.
- **Human owns:** confirming each efficacy figure against its cited source,
  and adjudicating when sources disagree.

## Tooling — build in this order
1. **Schema validator (build first).** A small script (JSON Schema / Zod /
   Python) that checks every `data/drugs/*.json` conforms. High leverage:
   catches schema drift the moment drug #2 or #3 doesn't fit the
   endpoint-agnostic / event-based model. Cheap to build.
2. **CT.gov API pre-fill helper (defer).** Do NOT build now. Rationale: the
   registry supplies only the *skeleton* (trial IDs, phases, dates, sponsor,
   enrollment) — NOT the judgment-heavy efficacy layer (met?, endpoint role,
   accelerated-approval ordering), which comes from press releases and
   journals. Automating the skeleton doesn't remove the real bottleneck, and
   the schema is still moving. Build only when: (a) schema is frozen after
   ~5–10 hand-built drugs, and (b) drug count is scaling past ~20. Even then,
   scope it to skeleton-only pre-fill; efficacy stays hand-curated on top.

## Status
- Schema proven on 1 drug (sotorasib). Not yet frozen.
- No tooling built yet. Manual curation is faster than automation at this N.
