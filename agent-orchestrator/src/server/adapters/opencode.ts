import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

function resolveOpenCodeAgent(input: AdapterSpawnInput): string {
  if (input.preferredAgent) {
    return input.preferredAgent;
  }
  switch (input.task.taskType) {
    case "planning":
    case "explore":
      return "plan";
    case "implement":
    case "refactor":
    case "test-fix":
      return "build";
    default:
      return "general";
  }
}

export class OpenCodeAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "opencode",
      provider: "opencode",
      title: "OpenCode",
      commandCandidates: ["opencode", "open-code"],
      versionProbe: ["--version"],
      models: ["openai/gpt-4.1", "anthropic/claude-sonnet-4", "google/gemini-2.5-pro"],
      supportsNativeSubagents: true,
      supportsCloud: false,
      supportsContextStats: true,
      supportsCompaction: true,
      supportsModelSelection: true,
      supportsModeSelection: true,
      supportsBestOfN: false,
      supportsInternetControl: true,
      supportsReadOnlyPlanMode: true,
      supportsWorktreeExecution: true,
      exactUsageSupported: false,
      nativeStatsSupported: true,
      maxContextWindow: 256000,
      maxOutputTokens: 32000,
      costTier: "medium",
      telemetryConfidence: 0.4,
      notes: [
        "supports explicit primary agents like plan/build and subagents like general/explore",
        "command flags are modeled conservatively to keep future provider expansion behind the same adapter contract"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    const args = ["run", "--agent", resolveOpenCodeAgent(input)];

    if (input.plan.model) {
      args.push("--model", input.plan.model);
    }

    if (input.maxIterations) {
      args.push("--max-steps", String(input.maxIterations));
    }

    if (input.plan.agentMode === "read_only_strategist") {
      args.push("--read-only");
    }

    args.push(this.formatPrompt(input));
    return args;
  }
}
