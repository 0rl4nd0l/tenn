import type { ExecutionPlan, LogRecord, RunRecord, SessionRecord, TaskRecord, WorktreeRecord } from "../../shared/types";
import type { AdapterTaskHandle } from "../adapters/base";
import { AdapterRegistry } from "../adapters";
import { createId } from "../utils/id";
import { nowIso } from "../utils/time";

import { OwnershipLockManager } from "./locks";
import { WorktreeManager } from "./worktrees";

export interface SpawnResult {
  run: RunRecord;
  session: SessionRecord;
  logs: LogRecord[];
  worktree: WorktreeRecord | null;
  handle: AdapterTaskHandle;
}

export interface SpawnerOptions {
  repoRoot: string;
  adapterRegistry: AdapterRegistry;
  worktreeManager: WorktreeManager;
  lockManager: OwnershipLockManager;
}

export class TaskSpawner {
  constructor(private readonly options: SpawnerOptions) {}

  async spawnTask(task: TaskRecord, plan: ExecutionPlan, prompt: string): Promise<SpawnResult> {
    let worktree: WorktreeRecord | null = null;
    try {
      if (plan.useWorktree) {
        worktree = await this.options.worktreeManager.create(task.id);
      }
      if (task.ownedFiles.length > 0) {
        this.options.lockManager.acquire(task.id, task.ownedFiles, "write");
      }

      const runId = createId("run");
      const sessionId = createId("session");
      const logs: LogRecord[] = [];
      const handle = await this.options.adapterRegistry.get(plan.runtime).spawn({
        task,
        plan,
        cwd: worktree?.path ?? this.options.repoRoot,
        prompt,
        addWritableDirs: worktree ? [worktree.path] : [],
        cloudEnvironmentId: extractCloudEnvironmentId(task),
        maxIterations: plan.maxIterations
      });

      if (handle.process) {
        handle.process.child.stdout?.on("data", (chunk: Buffer | string) => {
          logs.push(makeLog(runId, "stdout", chunk.toString()));
        });
        handle.process.child.stderr?.on("data", (chunk: Buffer | string) => {
          logs.push(makeLog(runId, "stderr", chunk.toString()));
        });
      }

      const session: SessionRecord = {
        id: sessionId,
        taskId: task.id,
        runtime: plan.runtime,
        provider: plan.provider,
        model: plan.model,
        mode: plan.agentMode,
        localOrCloud: plan.locality,
        nativeStatsSupported: handle.capability.nativeStatsSupported,
        exactUsageSupported: handle.capability.exactUsageSupported,
        compactionSupported: handle.capability.supportsCompaction,
        contextWindow: handle.capability.maxContextWindow,
        maxOutputTokens: handle.capability.maxOutputTokens,
        estimatedContextUsed: task.tokenBudget.sessionOccupancyEstimate,
        nativeContextUsed: null,
        headroom: task.tokenBudget.headroomRatio,
        quotaState: handle.capability.quotaState,
        status: "running",
        externalSessionId: handle.externalId,
        startedAt: nowIso(),
        updatedAt: nowIso()
      };

      const run: RunRecord = {
        id: runId,
        taskId: task.id,
        sessionId,
        attempt: task.attempts + 1,
        status: "running",
        startedAt: nowIso(),
        endedAt: null,
        exitCode: null,
        summary: `Spawned via ${plan.runtime}`
      };

      return {
        run,
        session,
        logs,
        worktree,
        handle
      };
    } catch (error) {
      if (worktree) {
        await this.options.worktreeManager.cleanup(worktree).catch(() => undefined);
      }
      throw error;
    }
  }
}

function makeLog(runId: string, stream: LogRecord["stream"], message: string): LogRecord {
  return {
    id: createId("log"),
    runId,
    stream,
    message,
    createdAt: nowIso()
  };
}

function extractCloudEnvironmentId(task: TaskRecord): string | null {
  const raw = task.constraints["cloudEnvironmentId"];
  return typeof raw === "string" && raw.trim().length > 0 ? raw : null;
}
