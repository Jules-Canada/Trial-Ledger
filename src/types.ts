// Types mirror docs/drug-schema.md. The drug record is the atomic unit;
// every view is an aggregation over these. See CLAUDE.md.

export type SourceType =
  | "registry"
  | "press_release"
  | "IR"
  | "journal"
  | "conference_abstract"
  | "fda_label"
  | "drugs_at_fda"
  | "other";

export interface Source {
  url: string;
  source_type: SourceType;
}

export type EndpointRole = "primary" | "secondary" | "exploratory";

export interface EfficacyRecord {
  trial: string;
  phase: string;
  endpoint: string;
  value: number | null;
  unit: string;
  role: EndpointRole;
  /** met? is per-endpoint, not per-phase. null = single-arm / no formal bar. */
  met: boolean | null;
  comparator?: string;
  note?: string;
  sources: Source[];
}

export type TimelineEventType =
  | "first_in_human"
  | "phase_start"
  | "filing"
  | "accelerated_approval"
  | "approval"
  | "data_readout"
  | "regulatory_event"
  | "discontinuation";

export interface TimelineEvent {
  date: string | null;
  type: TimelineEventType;
  trial?: string;
  confirmed?: boolean;
  note?: string;
  sources: Source[];
}

export interface Trial {
  id: string;
  name: string;
  registry_id: string;
  phases: string[];
  start_date: string | null;
  status: string;
  note?: string;
  sources: Source[];
}

export interface Identity {
  name: string;
  codes: string[];
  brand_name: string;
  sponsors: string[];
  modality: string;
  target: string;
  indications: string[];
}

export interface Drug {
  id: string;
  _verification?: { status: string; verified_on?: string; note?: string };
  identity: Identity;
  trials: Trial[];
  timeline: TimelineEvent[];
  efficacy: EfficacyRecord[];
  discontinuation: unknown | null;
}

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
