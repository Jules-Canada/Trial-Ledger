// The drug record is the atomic unit; every view is an aggregation over these.
// See CLAUDE.md. The record SHAPE is generated from the canonical Pydantic
// schema (pipeline/schema.py) into ./types.generated.ts — regenerate with
// `tl-gen-types`. This file re-exports those types and adds frontend-only
// helpers, so hand-written UI logic and the schema stay in one place each.

export type {
  Source,
  SourceType,
  EndpointRole,
  EfficacyRecord,
  TimelineEventType,
  TimelineEvent,
  Trial,
  Identity,
  Discontinuation,
  Verification,
  Drug,
} from "./types.generated";

import type { Source, SourceType } from "./types.generated";

/** Primary-evidence source types get a solid underline; topline gets dashed. */
export const PRIMARY_EVIDENCE: SourceType[] = [
  "journal",
  "registry",
  "fda_label",
  "drugs_at_fda",
];

export function hasPrimaryEvidence(sources: Source[]): boolean {
  return sources.some((s) => PRIMARY_EVIDENCE.includes(s.source_type));
}
