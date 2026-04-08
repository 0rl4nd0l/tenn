import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

export class CursorAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "cursor",
      provider: "cursor",
      title: "Cursor",
      commandCandidates: ["cursor-agent", "cursor"],
      versionProbe: ["--version"],
      models: ["cursor-small", "cursor-fast", "gpt-4.1"],
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
      maxContextWindow: 128000,
      maxOutputTokens: 16000,
      costTier: "medium",
      telemetryConfidence: 0.3,
      notes: [
        "cursor runtime support is conservative in V1",
        "installation detection may resolve from the desktop app or future CLI binaries"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    return [this.formatPrompt(input)];
  }
}
