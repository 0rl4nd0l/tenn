import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

/**
 * Default OpenCode server URL for the shared-server pattern.
 *
 * When OPENCODE_SERVER_URL is set, the adapter uses `opencode attach` instead
 * of `opencode run`, connecting to a single long-lived server process. This
 * avoids spawning a full Node + Pyright runtime per task (~2 GB each) and
 * instead creates lightweight TUI clients (~50 MB each).
 *
 * Start the server once:
 *   opencode serve --port 4096
 *
 * Then set the env var:
 *   OPENCODE_SERVER_URL=http://localhost:4096
 */
const OPENCODE_SERVER_URL = process.env.OPENCODE_SERVER_URL ?? "";

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
        "set OPENCODE_SERVER_URL to use shared-server mode (recommended for multi-session)",
        "shared-server mode: one Pyright + one runtime shared across all tasks"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    if (OPENCODE_SERVER_URL) {
      return this.buildAttachArgs(input);
    }
    return this.buildRunArgs(input);
  }

  /** Standalone mode: spawns a full opencode process per task (~2 GB each). */
  private buildRunArgs(input: AdapterSpawnInput): string[] {
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

  /** Shared-server mode: attaches to a running `opencode serve` instance (~50 MB each). */
  private buildAttachArgs(input: AdapterSpawnInput): string[] {
    const args = ["attach", OPENCODE_SERVER_URL];

    if (input.cwd) {
      args.push("--dir", input.cwd);
    }

    args.push(this.formatPrompt(input));
    return args;
  }
}
