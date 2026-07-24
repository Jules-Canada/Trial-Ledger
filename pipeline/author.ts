import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ClaudeProvider } from "./llm/claude";
import type { LlmProvider } from "./llm/provider";
import { DRUG_RECORD_SCHEMA, authoringPrompt } from "./authoring-schema";

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
  const id =
    (typeof record.id === "string" && record.id) ||
    drug.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  record.id = id;
  // Trust is provenance-based: stamp which model authored this, not a human sign-off.
  record._verification = {
    status: "draft-unverified",
    note: `Auto-authored by ${result.provider}/${result.model}. Provenance-based trust: source_type per data point signals confidence. Run npm run validate.`,
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
