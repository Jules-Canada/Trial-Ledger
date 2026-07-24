#!/usr/bin/env node
// Schema validator for data/drugs/*.json — see docs/drug-schema.md.
// Dependency-free on purpose (the "build the validator first, small script"
// call in docs/data-pipeline.md). Run: `npm run validate`.
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DRUGS_DIR = join(ROOT, "data", "drugs");

const SOURCE_TYPES = new Set([
  "registry",
  "press_release",
  "IR",
  "journal",
  "conference_abstract",
  "fda_label",
  "drugs_at_fda",
  "other",
]);
const EVENT_TYPES = new Set([
  "first_in_human",
  "phase_start",
  "filing",
  "accelerated_approval",
  "approval",
  "data_readout",
  "regulatory_event",
  "discontinuation",
]);
const ROLES = new Set(["primary", "secondary", "exploratory"]);

const isStr = (v) => typeof v === "string" && v.length > 0;
const isNumOrNull = (v) => v === null || typeof v === "number";
const isBoolOrNull = (v) => v === null || typeof v === "boolean";

function validateSources(sources, path, errs) {
  if (!Array.isArray(sources)) {
    errs.push(`${path}: sources must be an array`);
    return;
  }
  sources.forEach((s, i) => {
    if (!isStr(s?.url)) errs.push(`${path}[${i}]: source.url missing`);
    if (!SOURCE_TYPES.has(s?.source_type))
      errs.push(`${path}[${i}]: invalid source_type "${s?.source_type}"`);
  });
}

function validateDrug(drug, errs) {
  if (!isStr(drug.id)) errs.push("id: missing");

  const id = drug.identity ?? {};
  if (!isStr(id.name)) errs.push("identity.name: missing");
  if (!Array.isArray(id.sponsors) || id.sponsors.length === 0)
    errs.push("identity.sponsors: must be a non-empty array");
  if (!isStr(id.modality)) errs.push("identity.modality: missing");
  if (!isStr(id.target)) errs.push("identity.target: missing");
  if (!Array.isArray(id.indications) || id.indications.length === 0)
    errs.push("identity.indications: must be a non-empty array");

  const trialIds = new Set();
  if (!Array.isArray(drug.trials)) errs.push("trials: must be an array");
  else
    drug.trials.forEach((t, i) => {
      const p = `trials[${i}]`;
      if (!isStr(t.id)) errs.push(`${p}.id: missing`);
      else trialIds.add(t.id);
      if (!isStr(t.name)) errs.push(`${p}.name: missing`);
      if (!Array.isArray(t.phases) || t.phases.length === 0)
        errs.push(`${p}.phases: must be a non-empty array`);
      if (!isStr(t.indication)) errs.push(`${p}.indication: missing`);
      const okSponsor =
        isStr(t.sponsor) ||
        (Array.isArray(t.sponsor) && t.sponsor.length > 0 && t.sponsor.every(isStr));
      if (!okSponsor)
        errs.push(`${p}.sponsor: must be a non-empty string or string[]`);
      if (!(t.start_date === null || isStr(t.start_date)))
        errs.push(`${p}.start_date: must be a string or null`);
      validateSources(t.sources, `${p}.sources`, errs);
    });

  if (!Array.isArray(drug.timeline)) errs.push("timeline: must be an array");
  else
    drug.timeline.forEach((e, i) => {
      const p = `timeline[${i}]`;
      if (!(e.date === null || isStr(e.date)))
        errs.push(`${p}.date: must be a string or null`);
      if (!EVENT_TYPES.has(e.type))
        errs.push(`${p}.type: invalid event type "${e.type}"`);
      // trial is optional and may be null (e.g. a corporate event, no trial)
      if (e.trial != null && !trialIds.has(e.trial))
        errs.push(`${p}.trial: "${e.trial}" does not match any trial id`);
      validateSources(e.sources, `${p}.sources`, errs);
    });

  if (!Array.isArray(drug.efficacy)) errs.push("efficacy: must be an array");
  else
    drug.efficacy.forEach((r, i) => {
      const p = `efficacy[${i}] (${r.endpoint ?? "?"})`;
      if (!trialIds.has(r.trial))
        errs.push(`${p}.trial: "${r.trial}" does not match any trial id`);
      if (!isStr(r.phase)) errs.push(`${p}.phase: missing`);
      if (!isStr(r.endpoint)) errs.push(`${p}.endpoint: missing`);
      if (!isNumOrNull(r.value)) errs.push(`${p}.value: must be a number or null`);
      // unit may be "" for unitless endpoints (e.g. composite scores like TIS)
      if (typeof r.unit !== "string") errs.push(`${p}.unit: must be a string ("" if none)`);
      if (!ROLES.has(r.role)) errs.push(`${p}.role: invalid role "${r.role}"`);
      if (!isBoolOrNull(r.met)) errs.push(`${p}.met: must be true/false/null`);
      if (r.comparable !== undefined && typeof r.comparable !== "boolean")
        errs.push(`${p}.comparable: must be boolean if present`);
      validateSources(r.sources, `${p}.sources`, errs);
    });

  if (!("discontinuation" in drug))
    errs.push("discontinuation: missing (use null if not discontinued)");
}

// --- run ---
let files;
try {
  files = readdirSync(DRUGS_DIR).filter((f) => f.endsWith(".json"));
} catch {
  console.error(`Cannot read ${DRUGS_DIR}`);
  process.exit(1);
}

let failed = 0;
for (const file of files) {
  const errs = [];
  try {
    const drug = JSON.parse(readFileSync(join(DRUGS_DIR, file), "utf8"));
    validateDrug(drug, errs);
  } catch (e) {
    errs.push(`invalid JSON: ${e.message}`);
  }
  if (errs.length) {
    failed++;
    console.error(`✗ ${file}`);
    for (const e of errs) console.error(`    ${e}`);
  } else {
    console.log(`✓ ${file}`);
  }
}

console.log(`\n${files.length - failed}/${files.length} records valid.`);
process.exit(failed ? 1 : 0);
