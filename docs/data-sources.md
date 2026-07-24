# Data Sources

All data is public. No proprietary or company-internal data.

- **ClinicalTrials.gov** (bulk data / API) — trial phase, status, sponsor,
  dates, conditions. Primary source for timeline data.
- **Company press releases / IR pages** — topline efficacy results, phase
  transition announcements. Primary source for efficacy snapshots not
  captured in registry data.
- **FDA approval databases (Drugs@FDA)** — for the "launch" endpoint of the
  timeline.

## Workflow
- Output is a curated, versioned dataset (JSON/CSV) that the app reads from
  — not a live scraper hitting these sources on every page load.
- Start with manual curation per drug (see docs/roadmap.md for build order).
  Automate the ClinicalTrials.gov pull once the schema (docs/drug-schema.md)
  is proven out on a handful of real drugs.
