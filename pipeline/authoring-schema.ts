import type { JsonSchema } from "./llm/provider";

// Vendor-neutral JSON Schema for a drug record (mirrors docs/drug-schema.md).
// Structured-outputs constraints: additionalProperties:false on every object;
// no string length / numeric range constraints; optional fields are nullable.
const SOURCE = {
  type: "object",
  additionalProperties: false,
  properties: {
    url: { type: "string" },
    source_type: {
      type: "string",
      enum: [
        "registry",
        "press_release",
        "IR",
        "journal",
        "conference_abstract",
        "fda_label",
        "drugs_at_fda",
        "other",
      ],
    },
  },
  required: ["url", "source_type"],
} as const;

export const DRUG_RECORD_SCHEMA: JsonSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    id: { type: "string" },
    identity: {
      type: "object",
      additionalProperties: false,
      properties: {
        name: { type: "string" },
        codes: { type: "array", items: { type: "string" } },
        brand_name: { type: "string" },
        sponsors: { type: "array", items: { type: "string" } },
        modality: { type: "string" },
        target: { type: "string" },
        indications: { type: "array", items: { type: "string" } },
      },
      required: [
        "name",
        "codes",
        "brand_name",
        "sponsors",
        "modality",
        "target",
        "indications",
      ],
    },
    trials: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          id: { type: "string" },
          name: { type: "string" },
          registry_id: { type: "string" },
          indication: { type: "string" },
          sponsor: { type: "string" },
          phases: { type: "array", items: { type: "string" } },
          start_date: { type: ["string", "null"] },
          status: { type: "string" },
          note: { type: ["string", "null"] },
          sources: { type: "array", items: SOURCE },
        },
        required: [
          "id",
          "name",
          "registry_id",
          "indication",
          "sponsor",
          "phases",
          "start_date",
          "status",
          "note",
          "sources",
        ],
      },
    },
    timeline: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          date: { type: ["string", "null"] },
          type: {
            type: "string",
            enum: [
              "first_in_human",
              "phase_start",
              "filing",
              "accelerated_approval",
              "approval",
              "data_readout",
              "regulatory_event",
              "discontinuation",
            ],
          },
          trial: { type: ["string", "null"] },
          note: { type: ["string", "null"] },
          sources: { type: "array", items: SOURCE },
        },
        required: ["date", "type", "trial", "note", "sources"],
      },
    },
    efficacy: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          trial: { type: "string" },
          phase: { type: "string" },
          endpoint: { type: "string" },
          value: { type: ["number", "null"] },
          unit: { type: "string" },
          role: { type: "string", enum: ["primary", "secondary", "exploratory"] },
          met: { type: ["boolean", "null"] },
          comparator: { type: ["string", "null"] },
          note: { type: ["string", "null"] },
          sources: { type: "array", items: SOURCE },
        },
        required: [
          "trial",
          "phase",
          "endpoint",
          "value",
          "unit",
          "role",
          "met",
          "comparator",
          "note",
          "sources",
        ],
      },
    },
    discontinuation: {
      type: ["object", "null"],
      additionalProperties: false,
      properties: {
        date: { type: "string" },
        phase: { type: "string" },
        reason: { type: "string" },
      },
      required: ["date", "phase", "reason"],
    },
  },
  required: ["id", "identity", "trials", "timeline", "efficacy", "discontinuation"],
};

export function authoringPrompt(drug: string): string {
  return [
    `Build a single-drug clinical-development record for: ${drug}.`,
    "",
    "Rules:",
    "- Public sources only. Attach a source (url + source_type) to every data point.",
    "- Efficacy is endpoint-agnostic: capture whatever endpoint each trial reported",
    "  (ORR, PFS, OS, ACR20, PASI, PANSS, TIS, etc.) with its value, unit, role,",
    "  and met? (true/false/null). met? is PER-ENDPOINT, not per-phase.",
    "- A trial can span phases (e.g. Phase 1/2) and belongs to one indication and",
    "  one sponsor. Sponsorship can differ across trials (transfers over time).",
    "- Timeline is a set of dated events (non-linear: accelerated approval can",
    "  precede the confirmatory Phase 3 readout).",
    "- If a value is not disclosed, use null rather than inventing a number.",
    "- Set discontinuation only if the drug's development was halted.",
  ].join("\n");
}
