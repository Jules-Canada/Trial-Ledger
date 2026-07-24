// CT.gov skeleton pre-fill CLI. Emits trial stubs (matching docs/drug-schema.md)
// for one or more NCT IDs. Efficacy/timeline stay hand-/LLM-curated.
// Usage: npm run prefill NCT03600883 NCT04303780
import { fetchTrialSkeleton } from "./ctgov";

function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);
}

async function main(): Promise<void> {
  const ncts = process.argv.slice(2);
  if (!ncts.length) {
    console.error("Usage: npm run prefill <NCT_ID> [NCT_ID...]");
    process.exit(1);
  }
  const stubs = [];
  for (const nct of ncts) {
    const sk = await fetchTrialSkeleton(nct);
    if (!sk) {
      console.error(`! ${nct}: fetch failed`);
      continue;
    }
    const name = sk.acronym || sk.official_name;
    stubs.push({
      id: slug(sk.acronym || sk.official_name || nct),
      name,
      registry_id: sk.registry_id,
      indication: sk.conditions.join("; ") || "TODO: set indication",
      sponsor: sk.sponsor ?? "TODO: set sponsor",
      phases: sk.phases,
      start_date: sk.start_date,
      status: sk.status,
      note: `TODO: efficacy + timeline are curated. Enrollment: ${
        sk.enrollment ?? "?"
      }. Conditions: ${sk.conditions.join(", ") || "?"}.`,
      sources: [
        {
          url: `https://clinicaltrials.gov/study/${sk.registry_id}`,
          source_type: "registry",
        },
      ],
    });
  }
  console.log(JSON.stringify(stubs, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
