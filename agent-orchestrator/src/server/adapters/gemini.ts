import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

export class GeminiAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "gemini",
      provider: "google",
      title: "Gemini CLI",
      commandCandidates: ["gemini"],
      versionProbe: ["--version"],
      models: ["gemini-2.5-pro", "gemini-2.5-flash"],
      supportsNativeSubagents: false,
      supportsCloud: false,
      supportsContextStats: false,
      supportsCompaction: false,
      supportsModelSelection: true,
      supportsModeSelection: false,
      supportsBestOfN: false,
      supportsInternetControl: true,
      supportsReadOnlyPlanMode: true,
      supportsWorktreeExecution: true,
      exactUsageSupported: false,
      nativeStatsSupported: false,
      maxContextWindow: 1000000,
      maxOutputTokens: 32000,
      costTier: "medium",
      telemetryConfidence: 0.45,
      notes: [
        "favored for long-context exploration",
        "telemetry is estimated unless future CLI versions expose richer stats"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    const args = ["-p"];

    if (input.plan.model) {
      args.push("--model", input.plan.model);
    }

    args.push(this.formatPrompt(input));
    return args;
  }
}
