# Single-Drug Data Schema

The drug/asset is the atomic object in this system (see CLAUDE.md). Every
other view is an aggregation over these records — there is no separate
"pipeline" or "company" data structure.

This schema was revised after validating it end-to-end against sotorasib
(Lumakras). See docs/roadmap.md for what that validation surfaced.

## Fields

**Identity**
- Drug name / code (e.g. sotorasib / AMG 510)
- Sponsor(s)
- Modality (small molecule, biologic, cell therapy, etc.)
- Target
- Indication(s)

**Trials** (a drug has one or more trials; a single trial can span phases)
- Trial name + registry ID (e.g. CodeBreaK 100, NCT03600883)
- Phase(s) the trial covers — may be a range (e.g. "1/2"), not a single phase
- Start date, and status (ongoing / completed / terminated)

  > A trial is its own object because phases are NOT always discrete
  > transitions — sotorasib's CodeBreaK 100 was a single Phase 1/2 trial.
  > Efficacy attaches to a trial, not to a clean phase boundary.

**Timeline** (an ordered set of dated *events*, NOT a fixed linear sequence)
- Each event: date + type (e.g. IND/first-in-human, phase start, data readout,
  filing, approval, accelerated approval, discontinuation)
- The sequence is not fixed: accelerated approval can precede the confirmatory
  Phase 3 readout (as it did for sotorasib — approved May 2021 off Phase 2
  data; Phase 3 read out Aug 2022, after launch).
- If discontinued: date, phase at discontinuation, reason (if publicly known)

**Efficacy snapshots** (endpoint-agnostic — a list of endpoint records)
- Each record: endpoint name, value, unit, role (primary / secondary /
  exploratory), met? (Y/N), the trial/phase it belongs to, and source
  (link + source_type — see Sources)
- Endpoints vary per drug AND per phase — do NOT force a single fixed metric.
  The same endpoint can carry a different role across phases (e.g. OS was
  exploratory in sotorasib's Phase 1/2 but a formal secondary in Phase 3).
- "met?" lives on each endpoint, not on the phase: a phase can meet its
  primary endpoint while missing a secondary (sotorasib Phase 3 met PFS but
  missed OS). "Primary endpoint met" is a *derived* rollup, not a stored field.
- **Absence is meaningful, not blank.** A metric not reported at a given
  trial/phase (not yet measured, or not disclosed) is signal — carry it as an
  explicit "not measured" state, not a missing row, so the gap reads as
  intentional (see the display pattern in docs/design/single-drug-view.md).
- **Cross-drug comparability is not guaranteed by this schema alone.** Two
  drugs can report the same endpoint `name` under different definitions
  (e.g. "response rate" measured differently across trials). Optional per-record
  `comparable: true/false` and/or a `definition` note flags this rather than
  silently plotting mismatched metrics on one axis. Add these once enough drugs
  exist that the risk is real — ties into the deferred normalization layer.
- Though named "efficacy", the record shape is general: it can hold any outcome
  type (safety, patient-reported, etc.). Use `endpoint` (name) to disambiguate.

**Sources** (every data point carries at least one source)
- Each source: link + **source_type**, one of:
  `registry` (ClinicalTrials.gov) · `press_release` / `IR` ·
  `journal` (peer-reviewed) · `conference_abstract` · `fda_label` /
  `drugs_at_fda` · `other`.
- **Capture philosophy: expansive, not gated.** Press releases and abstracts
  ARE included — do not exclude a data point for lacking a primary source.
  Instead flag its source_type so credibility is transparent and the reader
  (or the visual) can weigh it. Flag provenance; don't drop data.
- When sources disagree, keep both and note the conflict rather than picking one.

## Out of scope (for now)
- Post-launch regulatory events (label changes, post-approval scrutiny) — has
  no home in the schema yet; revisit if a view needs it.

## Notes
- Schema was validated by fully populating it against sotorasib end-to-end.
  Re-validate against a discontinued/failed drug before assuming the
  discontinuation branch is right — it went unexercised (sotorasib is approved).
- Efficacy is endpoint-agnostic by design (resolved decision, not open).
