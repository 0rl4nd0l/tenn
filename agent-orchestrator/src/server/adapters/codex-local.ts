import type { AdapterSpawnInput } from "./base";
import { CliAdapter } from "./cli-adapter";

export class CodexLocalAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "codex-local",
      provider: "openai",
      title: "Codex CLI Local",
      commandCandidates: ["codex"],
      versionProbe: ["--version"],
      authProbe: {
        command: "codex",
        args: ["login", "status"],
        parser: (result) =>
          result.ok && /logged in/i.test(`${result.stdout}\n${result.stderr}`) ? "authenticated" : "logged_out"
      },
      models: ["gpt-5.4", "gpt-5.4-mini", "o4-mini"],
      supportsNativeSubagents: true,
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
      maxContextWindow: 200000,
      maxOutputTokens: 32000,
      costTier: "medium",
      telemetryConfidence: 0.72,
      notes: [
        "spawned through `codex exec`",
        "native subagents exist product-side, but this adapter keeps orchestration-level routing in control"
      ]
    });
  }

  protected buildSpawnArgs(input: AdapterSpawnInput): string[] {
    const args = [
      "exec",
      "--cd",
      this.resolveWorktreeCwd(input),
      "--sandbox",
      input.plan.useWorktree ? "workspace-write" : "read-only",
      "--json",
      "--skip-git-repo-check"
    ];

    if (input.plan.model) {
      args.push("--model", input.plan.model);
    }

    this.addCommonWriteControls(input, args);

    if (input.plan.internetAccess === "required") {
      args.push("--search");
    }

    args.push(this.formatPrompt(input));
    return args;
  }
}
