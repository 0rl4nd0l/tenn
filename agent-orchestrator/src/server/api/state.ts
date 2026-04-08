import type {
  BoardState,
  DashboardStats,
  HeadroomBand,
  ProjectSnapshot,
  ProviderCapabilitySnapshot,
  TaskDetailPayload,
  TaskRecord
} from "../../shared/types";
import type { StoreCollections } from "../db/database";

import { TaskScheduler } from "../core/scheduler";

export function buildBoardState(
  goalId: string,
  collections: StoreCollections,
  scheduler = new TaskScheduler(),
  projectSnapshot: ProjectSnapshot | null = null
): BoardState {
  return {
    goalId,
    conversation: collections.conversation,
    tasks: collections.tasks,
    sessions: collections.sessions,
    runs: collections.runs,
    logs: collections.logs,
    events: collections.events,
    janitorResults: collections.janitorResults,
    reviews: collections.reviews,
    locks: collections.locks,
    worktrees: collections.worktrees,
    capabilities: collections.capabilities,
    projectSnapshot,
    stats: buildDashboardStats(collections.tasks, collections.capabilities, scheduler)
  };
}

export function buildTaskDetailPayload(
  collections: StoreCollections,
  taskId: string,
  diffText: string
): TaskDetailPayload | null {
  const task = collections.tasks.find((candidate) => candidate.id === taskId);
  if (!task) {
    return null;
  }

  const children = collections.tasks.filter((candidate) => candidate.parentId === taskId);
  const dependencies = collections.tasks.filter((candidate) => task.dependencies.includes(candidate.id));
  const runs = collections.runs.filter((run) => run.taskId === taskId);
  const runIds = new Set(runs.map((run) => run.id));
  const session = collections.sessions.find((candidate) => candidate.taskId === taskId) ?? null;
  const entityIds = new Set<string>([taskId, ...runs.map((run) => run.id)]);
  if (session) {
    entityIds.add(session.id);
  }

  return {
    task,
    children,
    dependencies,
    session,
    runs,
    events: collections.events.filter((event) => entityIds.has(event.entityId)),
    logs: collections.logs.filter((log) => runIds.has(log.runId)),
    janitorResults: collections.janitorResults.filter((result) => result.taskId === taskId),
    reviews: collections.reviews.filter((review) => review.taskId === taskId),
    locks: collections.locks.filter((lock) => lock.taskId === taskId),
    worktree: collections.worktrees.find((worktree) => worktree.taskId === taskId) ?? null,
    diffText
  };
}

function buildDashboardStats(
  tasks: TaskRecord[],
  capabilities: ProviderCapabilitySnapshot[],
  scheduler: TaskScheduler
): DashboardStats {
  return {
    queue: scheduler.queueMetrics(tasks),
    tokenBands: countBands(tasks),
    runtimeLoad: scheduler.runtimeLoad(tasks.length > 0 ? tasks : bootstrapLoad(capabilities))
  };
}

function countBands(tasks: TaskRecord[]): Record<HeadroomBand, number> {
  return tasks.reduce<Record<HeadroomBand, number>>(
    (accumulator, task) => {
      accumulator[task.tokenBudget.headroomBand] += 1;
      return accumulator;
    },
    {
      healthy: 0,
      caution: 0,
      compact_or_fork: 0,
      migrate: 0,
      hard_stop: 0
    }
  );
}

function bootstrapLoad(capabilities: ProviderCapabilitySnapshot[]): TaskRecord[] {
  return capabilities.map(
    (capability): TaskRecord => ({
      id: capability.runtime,
      goalId: "bootstrap",
      parentId: null,
      title: capability.title,
      description: capability.notes.join(" "),
      status: "backlog",
      role: "worker",
      taskType: "explore",
      agentMode: "single",
      delegationPolicy: "single",
      locality: capability.supportsCloud ? "cloud" : "local",
      runtimeCandidates: [capability.runtime],
      providerCandidates: [capability.provider],
      preferredRuntime: capability.runtime,
      preferredProvider: capability.provider,
      chosenRuntime: capability.runtime,
      chosenProvider: capability.provider,
      chosenModel: capability.models[0] ?? null,
      ownedFiles: [],
      readOnlyPaths: [],
      verificationPolicy: ["diff_sanity"],
      tokenBudget: {
        predictedPromptTokens: 0,
        predictedOutputTokens: 0,
        predictedGrowthTokens: 0,
        sessionOccupancyEstimate: 0,
        subagentOverheadTokens: 0,
        headroomRatio: 1,
        headroomBand: "healthy",
        tier: "estimated",
        confidence: capability.telemetryConfidence
      },
      dependencies: [],
      attempts: 0,
      maxAttempts: 1,
      routingRationale: null,
      constraints: {},
      createdAt: capability.detectedAt,
      updatedAt: capability.detectedAt
    })
  );
}
