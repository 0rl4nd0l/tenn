import path from "path";

import type {
  AgentMode,
  ExecutionPlan,
  ProviderCapabilitySnapshot,
  ProviderId,
  QuotaState,
  RuntimeId
} from "../../shared/types";
import {
  findFirstInstalledCommand,
  runCommand,
  spawnCommand,
  type CommandResult
} from "../utils/process";
import { nowIso } from "../utils/time";

import type {
  AdapterFollowUpInput,
  AdapterSpawnInput,
  AdapterTaskHandle,
  AgentAdapter
} from "./base";

interface AuthProbe {
  command: string;
  args: string[];
  parser: (result: CommandResult) => ProviderCapabilitySnapshot["authStatus"];
}

export interface CliAdapterDefinition {
  runtime: RuntimeId;
  provider: ProviderId;
  title: string;
  commandCandidates: string[];
  versionProbe?: string[];
  authProbe?: AuthProbe;
  models: string[];
  supportsNativeSubagents: boolean;
  supportsCloud: boolean;
  supportsContextStats: boolean;
  supportsCompaction: boolean;
  supportsModelSelection: boolean;
  supportsModeSelection: boolean;
  supportsBestOfN: boolean;
  supportsInternetControl: boolean;
  supportsReadOnlyPlanMode: boolean;
  supportsWorktreeExecution: boolean;
  exactUsageSupported: boolean;
  nativeStatsSupported: boolean;
  maxContextWindow: number;
  maxOutputTokens: number;
  costTier: ProviderCapabilitySnapshot["costTier"];
  quotaState?: QuotaState;
  telemetryConfidence: number;
  notes: string[];
}

export abstract class CliAdapter implements AgentAdapter {
  readonly runtime: RuntimeId;
  protected readonly definition: CliAdapterDefinition;

  protected constructor(definition: CliAdapterDefinition) {
    this.runtime = definition.runtime;
    this.definition = definition;
  }

  supportsNativeSubagents(mode: AgentMode): boolean {
    return this.definition.supportsNativeSubagents && (mode === "native_subagents" || mode === "hybrid");
  }

  async detectCapability(): Promise<ProviderCapabilitySnapshot> {
    const installedCommand = await findFirstInstalledCommand(this.definition.commandCandidates);
    let version: string | null = null;
    let authStatus: ProviderCapabilitySnapshot["authStatus"] =
      this.definition.authProbe ? "unknown" : "unsupported";
    const notes = [...this.definition.notes];

    if (installedCommand && this.definition.versionProbe) {
      const result = await runCommand(installedCommand, this.definition.versionProbe);
      version = result.stdout.trim() || result.stderr.trim() || null;
      if (!result.ok && result.stderr.trim()) {
        notes.push(`version probe failed: ${result.stderr.trim()}`);
      }
    }

    if (installedCommand && this.definition.authProbe) {
      const result = await runCommand(this.definition.authProbe.command, this.definition.authProbe.args);
      authStatus = this.definition.authProbe.parser(result);
    }

    return {
      runtime: this.definition.runtime,
      provider: this.definition.provider,
      title: this.definition.title,
      command: installedCommand,
      version,
      installStatus: installedCommand ? "installed" : "missing",
      authStatus,
      detectedAt: nowIso(),
      models: this.definition.models,
      supportsNativeSubagents: this.definition.supportsNativeSubagents,
      supportsCloud: this.definition.supportsCloud,
      supportsContextStats: this.definition.supportsContextStats,
      supportsCompaction: this.definition.supportsCompaction,
      supportsModelSelection: this.definition.supportsModelSelection,
      supportsModeSelection: this.definition.supportsModeSelection,
      supportsBestOfN: this.definition.supportsBestOfN,
      supportsInternetControl: this.definition.supportsInternetControl,
      supportsReadOnlyPlanMode: this.definition.supportsReadOnlyPlanMode,
      supportsWorktreeExecution: this.definition.supportsWorktreeExecution,
      exactUsageSupported: this.definition.exactUsageSupported,
      nativeStatsSupported: this.definition.nativeStatsSupported,
      maxContextWindow: this.definition.maxContextWindow,
      maxOutputTokens: this.definition.maxOutputTokens,
      costTier: this.definition.costTier,
      quotaState: this.definition.quotaState ?? "unknown",
      telemetryConfidence: this.definition.telemetryConfidence,
      notes
    };
  }

  async spawn(input: AdapterSpawnInput): Promise<AdapterTaskHandle> {
    const capability = await this.detectCapability();
    const executable = capability.command;
    if (!executable) {
      throw new Error(`${this.runtime} is not installed`);
    }

    const childProcess = spawnCommand(executable, this.buildSpawnArgs(input), {
      cwd: input.cwd,
      env: {
        ...globalThis.process.env,
        ...input.extraEnv
      },
      onStdout: () => undefined,
      onStderr: () => undefined
    });

    return {
      runtime: this.runtime,
      capability,
      externalId: null,
      mode: "process",
      process: childProcess,
      wait: childProcess.wait,
      cancel: childProcess.cancel,
      isAlive: childProcess.isAlive
    };
  }

  async followUp(input: AdapterFollowUpInput): Promise<AdapterTaskHandle> {
    const capability = await this.detectCapability();
    const executable = capability.command;
    if (!executable) {
      throw new Error(`${this.runtime} is not installed`);
    }

    const args = this.buildFollowUpArgs(input);
    const childProcess = spawnCommand(executable, args, {
      cwd: input.cwd,
      env: {
        ...globalThis.process.env,
        ...input.extraEnv
      }
    });

    return {
      runtime: this.runtime,
      capability,
      externalId: input.externalTaskId ?? null,
      mode: "process",
      process: childProcess,
      wait: childProcess.wait,
      cancel: childProcess.cancel,
      isAlive: childProcess.isAlive
    };
  }

  async cancel(_sessionId: string): Promise<void> {
    return;
  }

  async isAlive(_sessionId: string): Promise<boolean> {
    return false;
  }

  protected addCommonWriteControls(input: AdapterSpawnInput, args: string[]): void {
    for (const directory of input.addWritableDirs ?? []) {
      args.push("--add-dir", directory);
    }
  }

  protected formatPrompt(input: AdapterSpawnInput | AdapterFollowUpInput): string {
    const constraints = [
      `Task: ${input.task.title}`,
      `Type: ${input.task.taskType}`,
      `Role: ${input.task.role}`,
      `Agent mode: ${input.plan.agentMode}`,
      `Delegation mode: ${input.plan.delegationMode}`,
      `Scope: ${input.task.description}`
    ];
    if (input.task.ownedFiles.length > 0) {
      constraints.push(`Owned files: ${input.task.ownedFiles.join(", ")}`);
    }
    if (input.task.readOnlyPaths.length > 0) {
      constraints.push(`Read-only paths: ${input.task.readOnlyPaths.join(", ")}`);
    }
    constraints.push(`Verification policy: ${input.task.verificationPolicy.join(", ") || "none"}`);
    constraints.push(`Routing rationale: ${input.plan.rationale.summary}`);
    return `${constraints.join("\n")}\n\nInstruction:\n${input.prompt}`;
  }

  protected resolveModeFlag(plan: ExecutionPlan): string {
    return plan.agentMode === "read_only_strategist" ? "plan" : "auto";
  }

  protected resolveWorktreeCwd(input: AdapterSpawnInput): string {
    return path.resolve(input.cwd);
  }

  protected buildFollowUpArgs(input: AdapterFollowUpInput): string[] {
    return this.buildSpawnArgs(input);
  }

  protected abstract buildSpawnArgs(input: AdapterSpawnInput): string[];
}
