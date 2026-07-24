#!/usr/bin/env node
// CT.gov skeleton pre-fill. Given one or more NCT IDs, fetch the AUTHORITATIVE
// registry fields and emit trial stubs matching docs/drug-schema.md.
//
// Skeleton ONLY — trial identity, phases, dates, sponsor, status, conditions.
// This is exactly the field set that was "to confirm" in our hand-built drafts.
// Efficacy/timeline stay hand-curated: the registry does NOT carry topline
// efficacy (met?, endpoint role, values). See docs/data-pipeline.md.
//
// Usage: node scripts/ctgov-prefill.mjs NCT03600883 NCT04303780

const API = "https://clinicaltrials.gov/api/v2/studies/";

const PHASE = { PHASE1: "1", PHASE2: "2", PHASE3: "3", PHASE4: "4" };
const STATUS = {
  COMPLETED: "completed",
  TERMINATED: "terminated",
  WITHDRAWN: "terminated",
  SUSPENDED: "terminated",
  RECRUITING: "ongoing",
  ENROLLING_BY_INVITATION: "ongoing",
  ACTIVE_NOT_RECRUITING: "ongoing",
  NOT_YET_RECRUITING: "ongoing",
};

function phasesOf(design) {
  const out = (design?.phases ?? []).map((p) => PHASE[p]).filter(Boolean);
  return out.length ? out : ["?"];
}

function slug(s) {
  return (s || "trial")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

async function fetchTrial(nct) {
  const res = await fetch(`${API}${encodeURIComponent(nct)}?format=json`, {
    headers: { accept: "application/json" },
  });
  if (!res.ok) throw new Error(`${nct}: HTTP ${res.status}`);
  const ps = (await res.json()).protocolSection ?? {};
  const idm = ps.identificationModule ?? {};
  const st = ps.statusModule ?? {};
  const design = ps.designModule ?? {};
  const spon = ps.sponsorCollaboratorsModule ?? {};
  const cond = ps.conditionsModule ?? {};

  const name = idm.acronym || idm.briefTitle || idm.officialTitle || nct;
  return {
    id: slug(idm.acronym || idm.briefTitle || nct),
    name,
    registry_id: idm.nctId || nct,
    indication: (cond.conditions ?? []).join("; ") || "TODO: set indication",
    sponsor: spon.leadSponsor?.name || "TODO: set sponsor",
    phases: phasesOf(design),
    start_date: st.startDateStruct?.date ?? null,
    status: STATUS[st.overallStatus] ?? (st.overallStatus || "unknown").toLowerCase(),
    note: `TODO: efficacy + timeline are hand-curated. Enrollment: ${
      design.enrollmentInfo?.count ?? "?"
    }. Conditions: ${(cond.conditions ?? []).join(", ") || "?"}.`,
    sources: [
      {
        url: `https://clinicaltrials.gov/study/${idm.nctId || nct}`,
        source_type: "registry",
      },
    ],
  };
}

const ncts = process.argv.slice(2);
if (!ncts.length) {
  console.error("Usage: node scripts/ctgov-prefill.mjs <NCT_ID> [NCT_ID...]");
  process.exit(1);
}

const out = [];
for (const nct of ncts) {
  try {
    out.push(await fetchTrial(nct));
  } catch (e) {
    console.error(`! ${e.message}`);
  }
}
console.log(JSON.stringify(out, null, 2));
