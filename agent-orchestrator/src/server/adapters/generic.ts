import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

export class GenericAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "generic",
      provider: "generic",
      title: "Generic CLI Adapter",
      commandCandidates: ["sh"],
      models: ["generic/default"],
      supportsNativeSubagents: false,
      supportsCloud: false,
      supportsContextStats: false,
      supportsCompaction: false,
      supportsModelSelection: false,
      supportsModeSelection: false,
      supportsBestOfN: false,
      supportsInternetControl: false,
      supportsReadOnlyPlanMode: false,
      supportsWorktreeExecution: true,
      exactUsageSupported: false,
      nativeStatsSupported: false,
      maxContextWindow: 64000,
      maxOutputTokens: 8000,
      costTier: "low",
      telemetryConfidence: 0.2,
      notes: ["fallback adapter for future providers or shell-backed prototypes"]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    return ["-lc", `printf %s ${JSON.stringify(this.formatPrompt(input))}`];
  }
}
