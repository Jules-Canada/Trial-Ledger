// ClinicalTrials.gov v2 API — authoritative trial skeleton. Shared by the
// authoring orchestrator (author.ts) and the prefill CLI (ctgov-prefill.ts).
// Skeleton ONLY (phases, dates, sponsor, status, conditions); the registry
// does NOT carry topline efficacy. See docs/data-pipeline.md.

const API = "https://clinicaltrials.gov/api/v2/studies/";

const PHASE: Record<string, string> = {
  PHASE1: "1",
  PHASE2: "2",
  PHASE3: "3",
  PHASE4: "4",
};
const STATUS: Record<string, string> = {
  COMPLETED: "completed",
  TERMINATED: "terminated",
  WITHDRAWN: "terminated",
  SUSPENDED: "terminated",
  RECRUITING: "ongoing",
  ENROLLING_BY_INVITATION: "ongoing",
  ACTIVE_NOT_RECRUITING: "ongoing",
  NOT_YET_RECRUITING: "ongoing",
};

export interface TrialSkeleton {
  registry_id: string;
  official_name: string;
  acronym: string | null;
  phases: string[];
  start_date: string | null;
  status: string;
  sponsor: string | null;
  conditions: string[];
  enrollment: number | null;
}

export function isNct(id: unknown): id is string {
  return typeof id === "string" && /^NCT\d{8}$/.test(id.trim());
}

export async function fetchTrialSkeleton(
  nct: string
): Promise<TrialSkeleton | null> {
  const res = await fetch(`${API}${encodeURIComponent(nct)}?format=json`, {
    headers: { accept: "application/json" },
  });
  if (!res.ok) return null;
  const ps = ((await res.json()) as { protocolSection?: Record<string, any> })
    .protocolSection ?? {};
  const idm = ps.identificationModule ?? {};
  const st = ps.statusModule ?? {};
  const design = ps.designModule ?? {};
  const spon = ps.sponsorCollaboratorsModule ?? {};
  const cond = ps.conditionsModule ?? {};

  const phases: string[] = (design.phases ?? [])
    .map((p: string) => PHASE[p])
    .filter(Boolean);

  return {
    registry_id: idm.nctId ?? nct,
    official_name: idm.briefTitle ?? idm.officialTitle ?? nct,
    acronym: idm.acronym ?? null,
    phases: phases.length ? phases : ["?"],
    start_date: st.startDateStruct?.date ?? null,
    status:
      STATUS[st.overallStatus] ?? (st.overallStatus || "unknown").toLowerCase(),
    sponsor: spon.leadSponsor?.name ?? null,
    conditions: cond.conditions ?? [],
    enrollment: design.enrollmentInfo?.count ?? null,
  };
}
