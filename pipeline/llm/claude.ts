import Anthropic from "@anthropic-ai/sdk";
import type {
  ExtractArgs,
  LlmProvider,
  LlmResult,
  ResearchArgs,
} from "./provider";

// Claude adapter. The ONLY file that imports the Anthropic SDK. Everything
// vendor-specific (structured outputs, server-side web tools) is contained here
// behind the vendor-neutral LlmProvider interface. Default model per the
// claude-api guidance: claude-opus-4-8 with adaptive thinking.
const MODEL = "claude-opus-4-8";

function textOf(message: Anthropic.Message): string {
  return message.content
    .map((b) => (b.type === "text" ? b.text : ""))
    .join("");
}

export class ClaudeProvider implements LlmProvider {
  readonly name = "claude";
  readonly model = MODEL;
  private client: Anthropic;

  constructor(client: Anthropic = new Anthropic()) {
    this.client = client;
  }

  async extract<T>({ system, prompt, schema }: ExtractArgs): Promise<LlmResult<T>> {
    // output_config.format is the canonical structured-outputs param; SDK types
    // may lag, so build params loosely and cast on the call.
    const params: Record<string, unknown> = {
      model: MODEL,
      max_tokens: 16000,
      thinking: { type: "adaptive" },
      output_config: { format: { type: "json_schema", schema } },
      messages: [{ role: "user", content: prompt }],
    };
    if (system) params.system = system;

    const message = (await this.client.messages.create(
      params as unknown as Anthropic.MessageCreateParamsNonStreaming
    )) as Anthropic.Message;
    const raw = textOf(message);
    return { data: JSON.parse(raw) as T, raw, provider: this.name, model: MODEL };
  }

  async research<T>({ system, brief, schema }: ResearchArgs): Promise<LlmResult<T>> {
    // Phase 1: gather a sourced digest with Claude's server-side web tools.
    const digest = await this.gather(brief);
    // Phase 2: reuse the vendor-neutral extraction path on the digest, so the
    // record shape has a single source of truth.
    const prompt = `${brief}\n\n--- RESEARCH DIGEST (with sources) ---\n${digest}`;
    return this.extract<T>({ system, prompt, schema });
  }

  private async gather(brief: string): Promise<string> {
    const messages: Anthropic.MessageParam[] = [
      {
        role: "user",
        content:
          "Research the following and produce a thorough, factual digest with " +
          "source URLs for every claim. Plain prose, not JSON.\n\n" +
          brief,
      },
    ];
    const params: Record<string, unknown> = {
      model: MODEL,
      max_tokens: 16000,
      thinking: { type: "adaptive" },
      tools: [
        { type: "web_search_20260209", name: "web_search" },
        { type: "web_fetch_20260209", name: "web_fetch" },
      ],
      messages,
    };
    // Server-side tools run automatically; on pause_turn, re-send to resume.
    for (let i = 0; i < 6; i++) {
      const message = (await this.client.messages.create(
        params as unknown as Anthropic.MessageCreateParamsNonStreaming
      )) as Anthropic.Message;
      if (message.stop_reason === "pause_turn") {
        messages.push({ role: "assistant", content: message.content });
        continue;
      }
      return textOf(message);
    }
    throw new Error("Claude research: exceeded max web-tool iterations");
  }
}
