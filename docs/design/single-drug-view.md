# Single-Drug View — Design Spec ("The Signal Ledger")

Milestone M3. The design of the single-drug "life story" view, settled before
any build (M4). Renders one `data/drugs/<id>.json` record. Reference example
throughout: sotorasib.

## The one insight
Efficacy evolution for a single drug: **how the efficacy signal holds up as the
evidence gets more rigorous** (single-arm early trials → randomized Phase 3).
The journey/timeline is scaffold; the signal evolution is the payload. The
static layout must be grokkable in <10s; the deployed tool then rewards
exploration (see Interaction). The shareable unit is the live URL, not a
screenshot.

## Direction: two stacked tracks sharing a left→right axis
1. **THE JOURNEY** — true-time timeline spine with event nodes.
2. **THE SIGNAL** — efficacy ledger grouped by trial, arranged along an
   **evidence-rigor** axis (low/single-arm on the left → high/randomized right).

Time and rigor mostly co-move, but accelerated approval sits *between* the two
trials — flagged on the JOURNEY track as happening BEFORE the high-rigor
evidence. That "approval before the confirmatory trial" kink is the editorial
hook, not a bug to smooth over.

Format: design desktop horizontal first (~1200×675, 16:9, social-landscape).
Mobile = later pass (rotate to vertical stack; journey → vertical spine,
signal groups stack).

## Desktop wireframe
```
┌──────────────────────────────────────────────────────────────────────────┐
│  KRAS G12C · NSCLC · AMGEN                                        [kicker] │
│  Cracking the 'undruggable' — then watching the signal narrow  [headline] │
│  Sotorasib hit an unprecedented target and won fast-track approval on      │
│  single-arm data. The randomized trial told a soberer story.  [standfirst] │
│                                                                            │
│  THE JOURNEY                                                               │
│  2018 ●──────────── 2020 ●──────── 2021 ★ ─────────────── 2022 ●          │
│  first-in-human      NDA filed   ACCELERATED             Phase 3 readout   │
│                                 APPROVAL (before P3!)                      │
│  ────────────────────────────────────────────────────────────────────    │
│  THE SIGNAL                                 evidence rigor ──────────▶     │
│                                                                            │
│   CodeBreaK 100 · Ph 1/2 · single-arm      CodeBreaK 200 · Ph 3 · vs docetaxel│
│   ● ORR  41%    ▁▁▁▁(journal)              ● ORR  28.1%  vs 13.2%  ▁▁▁▁    │
│   ● PFS  6.3mo                             ● PFS  5.6mo  vs 4.5mo          │
│   ◌ OS   12.5mo (exploratory)              ✕ OS   —      no benefit        │
│      "striking — but no comparator"           "real, but narrower"        │
│                                                                            │
│  ● met   ✕ missed   ◌ no formal bar    │  solid=journal  dashed=press rel. │
│  Sources: CodeBreaK 100 (JCO 2022) · CodeBreaK 200 (Lancet 2023) · as of Jul 2026│
└──────────────────────────────────────────────────────────────────────────┘
```

## Encoding system
- **met? (the derived layer):** `true` → filled dot ● (green); `false` → ✕
  (crimson); `null` (single-arm descriptive / exploratory) → open ring ◌
  (grey) meaning "no formal bar to hit". met? is per-endpoint, never per-phase.
- **role:** primary = larger/bolder marker + label; secondary/exploratory =
  lighter. Lets the eye find the endpoint that actually gated the phase.
- **source_type (provenance as polish):** underline under the value label —
  solid = primary evidence (journal / registry / fda_label); dashed = topline
  (press_release / conference_abstract). Makes credibility visible per the
  "capture expansive, flag provenance" decision.
- **value + unit** is the label; **comparator** (e.g. "vs 13.2%") as smaller
  secondary text where present.

## Editorial style (FT / Our World in Data)
- Warm off-white ground (~#FCFCFA / soft cream), ink #1A1A1A.
- Serif headline (editorial voice); clean sans for data labels (e.g. Inter).
- Restrained palette — 2 data colors + ink: met-green #1A8F5A, missed-crimson
  #D1495B, no-bar grey #9A9A9A, muted text #6B6B6B.
- Two anchored annotations carry the thesis ("striking — but no comparator" /
  "real, but narrower"). The point of view is the product.

## Data mapping (build should be mechanical)
- kicker ← identity.target · indication · sponsor
- journey nodes ← timeline[] (date, type); ★ = accelerated_approval
- signal groups ← trials[]; endpoints ← efficacy[] filtered by trial
- marker state ← efficacy.met (true/false/null); marker weight ← efficacy.role
- label ← efficacy.value + unit (+ comparator); underline ← source_type
- footer sources ← distinct efficacy/timeline sources; "as of" ← today

## Interaction (the tool is the artifact, not a screenshot)
The static Signal Ledger is the resting state; interaction is what makes it a
shareable *tool*. Layered so the <10s aha survives without any interaction:
- **Hover an endpoint** → tooltip with source(s), source_type, and the record's
  `note` (e.g. the OS caveat, the ORR 37%→41% supersession).
- **Hover/click a journey node** → the event `note` + a link out to the primary
  source (registry / press release / FDA).
- **Toggle raw vs. plain-language** endpoint labels (ORR ↔ "tumor shrinkage").
- Later, cross-drug: this single-drug view becomes a detail state you reach by
  clicking a drug in an aggregate view.
Keep interaction additive — never required to get the headline insight.

## Display pattern & scaling
- A metric with no reading at a trial/phase renders as a muted **"not measured"**
  row, never omitted — so the gap reads as intentional (schema treats absence as
  meaningful).
- Stacked endpoint rows read fine at 2–3 metrics. Past ~3 tracked outcomes per
  trial, switch to a **metric selector/toggle** (pick one metric; it drives the
  row shown and, in aggregate views, node/marker size).
- At small-multiple scale (many drugs tiled for the pipeline-shape view), per-
  trial card height should be **dynamic to metric count**, not fixed — a 1-metric
  drug and a 3-metric drug shouldn't force every tile to the same height.

## Open design questions (defer to build)
- Exact rigor-axis treatment when a drug has >2 trials or parallel trials.
- How annotations are authored: per-drug field in JSON vs. hand-placed.
- Mobile vertical layout (separate pass).
```
