# Clinical Development Visualizer

## Project Goal
Create an industry-inspiring, interactive visualization of the clinical
development journey — from early idea generation through Phase 1, Phase 2,
Phase 3, and launch. The tool should make the *shape* of pharma R&D pipelines
and the *evolution of efficacy signals* across phases immediately visible
and explorable.

## Who This Is For
- Primary: the creator, sharing as a life sciences thought-leadership piece
- Secondary: biotech/pharma professionals, investors, and analysts who want a
  quick visual gut-check on a company's pipeline or on efficacy trends by phase

## Core User Goals
1. **Pipeline shape** — quickly answer "what does Company X's development
   pipeline look like?" (count/stage/therapeutic area of assets across phases)
2. **Efficacy evolution** — show how outcomes (efficacy signals, endpoints hit)
   change as programs move Phase 1 → Phase 2 → Phase 3
3. **Virality / thought leadership** — the output is a polished, original,
   *interactive* tool at a real shareable URL: something life-sciences
   connections open, explore, and pass on. The shareable unit is the live link
   people interact with — NOT a static screenshot. Fast to grok (under 10
   seconds to the "aha"), with exploration rewarded beyond that.

## Architecture Principle: The Drug Is the Functional Unit
The atomic object in this system is a **single drug/asset** — not a company or
a pipeline. Every other view (pipeline shape, efficacy trends) is built by
aggregating drug records, never a separate data structure. This keeps the
model simple and makes expansion additive. Full schema: `docs/drug-schema.md`.

## Non-Goals (for now)
- Not a comprehensive trial database / regulatory tracker
- Not predictive modeling of trial success (descriptive/visual first)
- Not company-specific proprietary data — public sources only

## Tech Stack
- Frontend: React + D3.js (custom visuals) and/or Recharts (standard charts)
- Data layer: static JSON/CSV built by an offline data-prep pipeline
- Deployment: Vercel or Netlify for a real public URL
- No backend needed initially — static data, client-side rendering

## Design Principles
- Bold, editorial visual style — Financial Times / Our World in Data data
  journalism, but *interactive*: an explorable tool, not a static BI dashboard
  and not a screenshot.
- One clear insight per view up front, with interactive drill-down that
  rewards exploration (hover/click for sources, notes, detail).
- Works as a live, hosted experience on desktop and mobile. Deployment to a
  real public URL is core, not a final step. Looking good as a screenshot is a
  nice-to-have, not the goal.

## Reference Docs
- `docs/drug-schema.md` — full single-drug data schema
- `docs/data-sources.md` — data sources and curation workflow
- `docs/roadmap.md` — build order, status, and open questions (churns often)
