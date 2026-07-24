import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ClaudeProvider } from "./llm/claude";
import type { LlmProvider } from "./llm/provider";
import { DRUG_RECORD_SCHEMA, authoringPrompt } from "./authoring-schema";
import { fetchTrialSkeleton, isNct } from "./ctgov";

interface Source {
  url: string;
  source_type: string;
}
interface Trial {
  id: string;
  name: string;
  registry_id: string;
  indication: string;
  sponsor: string | string[];
  phases: string[];
  start_date: string | null;
  status: string;
  note?: string | null;
  sources: Source[];
}

// The LLM's trial skeleton (phases, dates, sponsor, status) is a guess; the
// registry is authoritative. For every trial with a real NCT, overwrite those
// fields from ClinicalTrials.gov and keep the LLM's id/indication/note/name
// (the id is what efficacy + timeline records link to; the registry's official
// title is uglier than the LLM's short name). See docs/design/authoring-pipeline.md.
async function mergePrefill(trials: Trial[]): Promise<number> {
  let filled = 0;
  await Promise.all(
    trials.map(async (t) => {
      if (!isNct(t.registry_id)) return;
      const sk = await fetchTrialSkeleton(t.registry_id.trim());
      if (!sk) {
        console.error(`[author] prefill: ${t.registry_id} fetch failed, keeping LLM values`);
        return;
      }
      t.phases = sk.phases;
      t.start_date = sk.start_date;
      t.status = sk.status;
      if (sk.sponsor) t.sponsor = sk.sponsor;
      if (!t.sources.some((s) => s.source_type === "registry")) {
        t.sources.unshift({
          url: `https://clinicaltrials.gov/study/${sk.registry_id}`,
          source_type: "registry",
        });
      }
      t.note = `${t.note ? t.note + " " : ""}[skeleton fields from ClinicalTrials.gov]`;
      filled++;
    })
  );
  return filled;
}

// Automated authoring orchestrator. Agent-agnostic: depends only on LlmProvider.
// Select provider via LLM_PROVIDER (default "claude"). See
// docs/design/authoring-pipeline.md.
function getProvider(): LlmProvider {
  const name = process.env.LLM_PROVIDER ?? "claude";
  switch (name) {
    case "claude":
      return new ClaudeProvider();
    default:
      throw new Error(
        `Unknown LLM_PROVIDER "${name}". Only "claude" is implemented so far.`
      );
  }
}

async function main(): Promise<void> {
  const drug = process.argv.slice(2).join(" ").trim();
  if (!drug) {
    console.error('Usage: npm run author "<drug name>"');
    process.exit(1);
  }

  const provider = getProvider();
  if (provider.name === "claude" && !process.env.ANTHROPIC_API_KEY) {
    console.error(
      "Missing ANTHROPIC_API_KEY. Provide it one of these ways (never commit it):\n" +
        "  • Keychain (most secure): ANTHROPIC_API_KEY=$(security find-generic-password -s ANTHROPIC_API_KEY -w) npm run author \"<drug>\"\n" +
        "  • .env.local (gitignored): copy .env.example to .env.local, fill it in, then npm run author \"<drug>\"\n" +
        "  • This session: type  ! export ANTHROPIC_API_KEY=sk-ant-...  then run the command."
    );
    process.exit(1);
  }
  const brief = authoringPrompt(drug);
  console.error(
    `[author] provider=${provider.name} model=${provider.model} drug="${drug}"`
  );

  // Prefer provider-native research (web gathering) when available; else extract
  // from the brief alone. CT.gov prefill merge is a TODO (see design doc).
  const result = provider.research
    ? await provider.research({ brief, schema: DRUG_RECORD_SCHEMA })
    : await provider.extract({ prompt: brief, schema: DRUG_RECORD_SCHEMA });

  const record = result.data as Record<string, unknown>;

  // Registry override: skeleton fields come from CT.gov, not the LLM.
  if (Array.isArray(record.trials)) {
    const n = await mergePrefill(record.trials as Trial[]);
    console.error(`[author] prefill: registry skeleton merged for ${n} trial(s)`);
  }

  const id =
    (typeof record.id === "string" && record.id) ||
    drug.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  record.id = id;
  // Trust is provenance-based: stamp which model authored this, not a human sign-off.
  record._verification = {
    status: "draft-unverified",
    note: `Auto-authored by ${result.provider}/${result.model}; trial skeleton fields (phases, dates, sponsor, status) merged from ClinicalTrials.gov. Provenance-based trust: source_type per data point signals confidence. Run npm run validate.`,
  };

  const root = join(dirname(fileURLToPath(import.meta.url)), "..");
  const out = join(root, "data", "drugs", `${id}.json`);
  writeFileSync(out, JSON.stringify(record, null, 2) + "\n");
  console.error(`[author] wrote ${out}\n[author] next: npm run validate`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
