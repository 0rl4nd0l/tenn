import type {
  AgentMode,
  ExecutionPlan,
  ProviderCapabilitySnapshot,
  RuntimeId,
  TaskRecord
} from "../../shared/types";
import type { CommandResult, SpawnedProcessHandle } from "../utils/process";

export interface AdapterSpawnInput {
  task: TaskRecord;
  plan: ExecutionPlan;
  cwd: string;
  prompt: string;
  sessionId?: string | null;
  externalTaskId?: string | null;
  addWritableDirs?: string[];
  bestOf?: number;
  cloudEnvironmentId?: string | null;
  preferredAgent?: string | null;
  maxIterations?: number | null;
  extraEnv?: NodeJS.ProcessEnv;
}

export interface AdapterFollowUpInput extends AdapterSpawnInput {
  sessionId: string;
}

export interface AdapterTaskHandle {
  runtime: RuntimeId;
  capability: ProviderCapabilitySnapshot;
  externalId: string | null;
  mode: "process" | "remote";
  wait: () => Promise<CommandResult>;
  cancel: () => Promise<void>;
  isAlive: () => boolean | Promise<boolean>;
  process?: SpawnedProcessHandle;
}

export interface AgentAdapter {
  readonly runtime: RuntimeId;
  detectCapability: () => Promise<ProviderCapabilitySnapshot>;
  spawn: (input: AdapterSpawnInput) => Promise<AdapterTaskHandle>;
  followUp: (input: AdapterFollowUpInput) => Promise<AdapterTaskHandle>;
  cancel: (sessionId: string, externalId?: string | null) => Promise<void>;
  isAlive: (sessionId: string, externalId?: string | null) => Promise<boolean>;
  supportsNativeSubagents: (mode: AgentMode) => boolean;
}
