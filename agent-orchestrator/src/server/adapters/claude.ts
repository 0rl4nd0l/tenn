import type { AdapterFollowUpInput, AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

export class ClaudeAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "claude",
      provider: "anthropic",
      title: "Claude Code",
      commandCandidates: ["claude"],
      versionProbe: ["--version"],
      authProbe: {
        command: "claude",
        args: ["auth", "status"],
        parser: (result) => (/\"loggedIn\":\s*true/i.test(result.stdout) ? "authenticated" : "logged_out")
      },
      models: ["sonnet", "opus", "claude-sonnet-4-6"],
      supportsNativeSubagents: true,
      supportsCloud: false,
      supportsContextStats: true,
      supportsCompaction: false,
      supportsModelSelection: true,
      supportsModeSelection: true,
      supportsBestOfN: false,
      supportsInternetControl: false,
      supportsReadOnlyPlanMode: true,
      supportsWorktreeExecution: true,
      exactUsageSupported: false,
      nativeStatsSupported: true,
      maxContextWindow: 200000,
      maxOutputTokens: 32000,
      costTier: "high",
      telemetryConfidence: 0.78,
      notes: [
        "uses Claude Code print mode for deterministic orchestration integration",
        "supports plan mode and explicit agents"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    const args = [
      "-p",
      "--output-format",
      "stream-json",
      "--permission-mode",
      input.plan.agentMode === "read_only_strategist" ? "plan" : "acceptEdits"
    ];

    if (input.plan.model) {
      args.push("--model", input.plan.model);
    }

    if (input.preferredAgent) {
      args.push("--agent", input.preferredAgent);
    }

    for (const directory of input.addWritableDirs ?? []) {
      args.push("--add-dir", directory);
    }

    args.push(this.formatPrompt(input));
    return args;
  }

  protected buildFollowUpArgs(input: AdapterFollowUpInput): string[] {
    const args = this.buildSpawnArgs(input);
    args.unshift("-r", input.sessionId);
    return args;
  }
}
