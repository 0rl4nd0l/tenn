import { runCommand } from "../utils/process";

import type { AdapterFollowUpInput, AdapterSpawnInput, AdapterTaskHandle } from "./base";
import { CliAdapter } from "./cli-adapter";

export class CodexCloudAdapter extends CliAdapter {
  constructor() {
    super({
      runtime: "codex-cloud",
      provider: "openai",
      title: "Codex Cloud",
      commandCandidates: ["codex"],
      versionProbe: ["--version"],
      authProbe: {
        command: "codex",
        args: ["login", "status"],
        parser: (result) =>
          result.ok && /logged in/i.test(`${result.stdout}\n${result.stderr}`) ? "authenticated" : "logged_out"
      },
      models: ["gpt-5.4", "gpt-5.4-mini"],
      supportsNativeSubagents: true,
      supportsCloud: true,
      supportsContextStats: false,
      supportsCompaction: false,
      supportsModelSelection: true,
      supportsModeSelection: false,
      supportsBestOfN: true,
      supportsInternetControl: true,
      supportsReadOnlyPlanMode: true,
      supportsWorktreeExecution: false,
      exactUsageSupported: false,
      nativeStatsSupported: false,
      maxContextWindow: 200000,
      maxOutputTokens: 32000,
      costTier: "medium",
      telemetryConfidence: 0.62,
      notes: [
        "submits detached Codex Cloud tasks with environment selection",
        "apply/diff/status remain explicit follow-up steps"
      ]
    });
  }

  async spawn(input: AdapterSpawnInput): Promise<AdapterTaskHandle> {
    const capability = await this.detectCapability();
    const executable = capability.command;
    if (!executable) {
      throw new Error("codex is not installed");
    }
    if (!input.cloudEnvironmentId) {
      throw new Error("codex-cloud requires a cloud environment id");
    }

    const args = [
      "cloud",
      "exec",
      "--env",
      input.cloudEnvironmentId,
      "--attempts",
      String(input.bestOf ?? 1),
      this.formatPrompt(input)
    ];

    const result = await runCommand(executable, args, {
      cwd: input.cwd,
      env: {
        ...process.env,
        ...input.extraEnv
      }
    });
    const externalId = extractCloudTaskId(result.stdout) ?? extractCloudTaskId(result.stderr);

    return {
      runtime: this.runtime,
      capability,
      externalId,
      mode: "remote",
      wait: async () => result,
      cancel: async () => undefined,
      isAlive: async () => false
    };
  }

  async followUp(input: AdapterFollowUpInput): Promise<AdapterTaskHandle> {
    const capability = await this.detectCapability();
    const executable = capability.command;
    if (!executable) {
      throw new Error("codex is not installed");
    }
    const externalId = input.externalTaskId ?? input.sessionId;
    const result = await runCommand(executable, ["cloud", "status", externalId], {
      cwd: input.cwd,
      env: {
        ...process.env,
        ...input.extraEnv
      }
    });

    return {
      runtime: this.runtime,
      capability,
      externalId,
      mode: "remote",
      wait: async () => result,
      cancel: async () => undefined,
      isAlive: async () => /running|queued|pending/i.test(`${result.stdout}\n${result.stderr}`)
    };
  }

  async cancel(): Promise<void> {
    return;
  }

  async isAlive(_sessionId: string, externalId?: string | null): Promise<boolean> {
    if (!externalId) {
      return false;
    }
    const capability = await this.detectCapability();
    if (!capability.command) {
      return false;
    }
    const result = await runCommand(capability.command, ["cloud", "status", externalId]);
    return /running|queued|pending/i.test(`${result.stdout}\n${result.stderr}`);
  }

  protected buildSpawnArgs(): string[] {
    return [];
  }
}

function extractCloudTaskId(output: string): string | null {
  const match = output.match(/[A-Za-z0-9_-]{8,}/);
  return match?.[0] ?? null;
}
