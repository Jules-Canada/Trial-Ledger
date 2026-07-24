// Agent-agnostic LLM provider interface. The authoring pipeline depends ONLY on
// this — never on a specific vendor SDK. Claude is the first implementation
// (see claude.ts); other providers implement the same interface with no change
// to the orchestrator. See docs/design/authoring-pipeline.md.

export type JsonSchema = Record<string, unknown>;

export interface ExtractArgs {
  system?: string;
  prompt: string;
  /** Vendor-neutral JSON Schema the output must conform to. */
  schema: JsonSchema;
}

export interface ResearchArgs {
  system?: string;
  brief: string;
  schema: JsonSchema;
}

export interface LlmResult<T> {
  data: T;
  raw: string;
  provider: string;
  model: string;
}

export interface LlmProvider {
  readonly name: string;
  readonly model: string;

  /** Extract schema-valid JSON from `prompt`. Every provider implements this. */
  extract<T>(args: ExtractArgs): Promise<LlmResult<T>>;

  /** Optional: provider gathers its own web sources for `brief`, then extracts.
   *  Providers without native web capability omit this; the orchestrator falls
   *  back to a separate gather step + extract(). */
  research?<T>(args: ResearchArgs): Promise<LlmResult<T>>;
}
