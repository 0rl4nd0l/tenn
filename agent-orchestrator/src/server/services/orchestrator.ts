import { EventEmitter } from "events";
import path from "path";

import type {
  BoardState,
  EventRecord,
  ExecutionPlan,
  JanitorCheckDefinition,
  JanitorResultRecord,
  LogRecord,
  ProviderId,
  ProjectSnapshot,
  ReviewDecisionRecord,
  RuntimeId,
  StrategistRunStartResponse,
  TaskDetailPayload,
  TaskRecord
} from "../../shared/types";
import { createAdapterRegistry, refreshCapabilities } from "../adapters";
import { buildBoardState, buildTaskDetailPayload } from "../api/state";
import { Janitor } from "../core/janitor";
import { OwnershipLockManager } from "../core/locks";
import { ProjectIntelligenceService } from "../core/project-intelligence";
import { TaskRouter } from "../core/router";
import { TaskScheduler } from "../core/scheduler";
import { StrategistRuntimeRunner } from "../core/strategist-runtime";
import { TaskSpawner } from "../core/spawner";
import { StrategistService, materializeTaskGraph } from "../core/strategist";
import { MemoryStreamBridge } from "../core/stream-bridge";
import { TokenBudgetManager } from "../core/token-budget";
import { WorktreeManager } from "../core/worktrees";
import { OrchestratorStore } from "../db/database";
import { ensureDir } from "../utils/filesystem";
import { createId } from "../utils/id";
import { runCommand } from "../utils/process";
import { nowIso } from "../utils/time";

export interface OrchestratorServiceOptions {
  repoRoot: string;
  dataDir?: string;
  goalId?: string;
  autoSchedule?: boolean;
}

interface ActiveTaskRun {
  taskId: string;
  runId: string;
  sessionId: string;
}

interface StrategistRunContext {
  runId: string;
  userMessageId: string;
  createdTaskIds: string[];
  rootTaskId: string | null;
}

interface PendingDelegationApproval {
  requestedAt: string;
  originalMessage: string;
  plan: ReturnType<StrategistService["plan"]>;
  projectSnapshot: ProjectSnapshot | null;
}

export class OrchestratorService extends EventEmitter {
  readonly goalId: string;
  private readonly store: OrchestratorStore;
  private readonly adapterRegistry = createAdapterRegistry();
  private readonly tokenBudgetManager = new TokenBudgetManager();
  private readonly router = new TaskRouter(this.tokenBudgetManager);
  private readonly scheduler = new TaskScheduler();
  private readonly strategist = new StrategistService();
  private readonly strategistRuntime = new StrategistRuntimeRunner();
  private readonly strategistStreams = new MemoryStreamBridge();
  private readonly janitor = new Janitor();
  private readonly lockManager: OwnershipLockManager;
  private readonly worktreeManager: WorktreeManager;
  private readonly spawner: TaskSpawner;
  private readonly projectIntelligence: ProjectIntelligenceService;
  private readonly activeRuns = new Map<string, ActiveTaskRun>();
  private readonly strategistChatCwd: string;
  private strategistSessionId: string | null = null;
  private strategistSessionRuntime: "codex-local" | "opencode" | null = null;
  private strategistSessionModel: string | null = null;
  private pendingDelegationApproval: PendingDelegationApproval | null = null;
  private mergeQueue: Promise<void> = Promise.resolve();
  private scheduling = false;
  private lastProjectSnapshot: ProjectSnapshot | null = null;

  private constructor(private readonly options: Required<OrchestratorServiceOptions>, store: OrchestratorStore) {
    super();
    this.store = store;
    this.goalId = options.goalId;
    const collections = this.store.getCollections(this.goalId);
    this.lockManager = new OwnershipLockManager(collections.locks);
    this.worktreeManager = new WorktreeManager(this.options.repoRoot, path.join(this.options.dataDir, "worktrees"));
    this.strategistChatCwd = path.join(this.options.dataDir, "chat-runtime");
    ensureDir(this.strategistChatCwd);
    this.spawner = new TaskSpawner({
      repoRoot: this.options.repoRoot,
      adapterRegistry: this.adapterRegistry,
      worktreeManager: this.worktreeManager,
      lockManager: this.lockManager
    });
    this.projectIntelligence = new ProjectIntelligenceService(this.options.repoRoot);
  }

  static async create(options: OrchestratorServiceOptions): Promise<OrchestratorService> {
    const resolved: Required<OrchestratorServiceOptions> = {
      repoRoot: options.repoRoot,
      dataDir: options.dataDir ?? path.join(options.repoRoot, "agent-orchestrator", ".data"),
      goalId: options.goalId ?? "default-goal",
      autoSchedule: options.autoSchedule ?? true
    };
    ensureDir(resolved.dataDir);
    const store = await OrchestratorStore.open(path.join(resolved.dataDir, "orchestrator.sqlite"));
    const service = new OrchestratorService(resolved, store);
    await service.seed();
    return service;
  }

  async dispose(): Promise<void> {
    this.store.destroy();
  }

  async getBoardState(): Promise<BoardState> {
    const collections = this.store.getCollections(this.goalId);
    const query = this.lastProjectSnapshot?.queryTerms.join(" ") ?? "";
    this.lastProjectSnapshot = await this.projectIntelligence.buildSnapshot(collections, query);
    return buildBoardState(this.goalId, collections, this.scheduler, this.lastProjectSnapshot);
  }

  async getTaskDetail(taskId: string): Promise<TaskDetailPayload | null> {
    const diffText = await this.getTaskDiff(taskId);
    return buildTaskDetailPayload(this.store.getCollections(this.goalId), taskId, diffText);
  }

  async refreshCapabilitySnapshots(): Promise<void> {
    const capabilities = await refreshCapabilities(this.adapterRegistry);
    this.store.replaceCapabilities(capabilities);
    this.emitRefresh("capabilities");
  }

  hasStrategistRun(runId: string): boolean {
    return this.strategistStreams.hasStream(runId);
  }

  subscribeStrategistRun(
    runId: string,
    options: {
      lastEventId?: string | null;
      onEntry: (entry: { id: string; event: string; data: Record<string, unknown> }) => void;
      onEnd: () => void;
    }
  ): () => void {
    return this.strategistStreams.subscribe(runId, options);
  }

  async startStrategistRun(
    message: string,
    options?: { runtime?: "codex-local" | "opencode" | null; model?: string | null }
  ): Promise<StrategistRunStartResponse> {
    const userMessage = {
      id: createId("msg"),
      role: "user" as const,
      content: message,
      createdAt: nowIso()
    };
    this.store.appendConversationMessage(this.goalId, userMessage);

    const collections = this.store.getCollections(this.goalId);
    const workspaceContext = await this.projectIntelligence.getStrategistContext(collections, message);
    this.lastProjectSnapshot = workspaceContext.snapshot;

    const approvalDecision = classifyDelegationApprovalResponse(message);
    if (this.pendingDelegationApproval && approvalDecision) {
      const pending = this.pendingDelegationApproval;
      this.pendingDelegationApproval = null;

      if (approvalDecision === "decline") {
        const runContext = this.createStrategistRunContext(userMessage.id, { rootTask: null, childTasks: [] });
        this.strategistStreams.createStream(runContext.runId);
        this.strategistStreams.publish(runContext.runId, "run.started", {
          runId: runContext.runId,
          userMessageId: userMessage.id,
          rootTaskId: null,
          createdTaskIds: []
        });
        this.completeStrategistRun(
          runContext,
          "Okay. I'll stay in chat and won't start execution unless you ask.",
          { mode: "approval" }
        );
        return {
          runId: runContext.runId,
          userMessageId: userMessage.id,
          createdTaskIds: [],
          rootTaskId: null
        };
      }

      const graph = materializeTaskGraph(pending.plan);
      this.applyChatRoutingPreferences(graph, options);
      const approvedRunContext = this.createStrategistRunContext(userMessage.id, graph);
      this.strategistStreams.createStream(approvedRunContext.runId);
      this.strategistStreams.publish(approvedRunContext.runId, "run.started", {
        runId: approvedRunContext.runId,
        userMessageId: userMessage.id,
        rootTaskId: approvedRunContext.rootTaskId,
        createdTaskIds: approvedRunContext.createdTaskIds
      });
      this.persistDelegatedGraph(approvedRunContext, graph);
      this.completeStrategistRun(
        approvedRunContext,
        buildDelegationAcceptedReply(pending.originalMessage, pending.projectSnapshot),
        { mode: "approval" }
      );
      if (this.options.autoSchedule && graph.rootTask) {
        await this.scheduleNow();
      }
      return {
        runId: approvedRunContext.runId,
        userMessageId: userMessage.id,
        createdTaskIds: approvedRunContext.createdTaskIds,
        rootTaskId: approvedRunContext.rootTaskId
      };
    }

    if (this.pendingDelegationApproval && !approvalDecision) {
      const repromptContext = this.createStrategistRunContext(userMessage.id, { rootTask: null, childTasks: [] });
      this.strategistStreams.createStream(repromptContext.runId);
      this.strategistStreams.publish(repromptContext.runId, "run.started", {
        runId: repromptContext.runId,
        userMessageId: userMessage.id,
        rootTaskId: null,
        createdTaskIds: []
      });
      this.completeStrategistRun(
        repromptContext,
        `I'm still waiting on "${this.pendingDelegationApproval.originalMessage}" — do you want me to proceed with that, or should I handle "${message}" instead?`,
        { mode: "approval_clarification" }
      );
      return {
        runId: repromptContext.runId,
        userMessageId: userMessage.id,
        createdTaskIds: [],
        rootTaskId: null
      };
    }

    const plan = this.strategist.plan(this.goalId, message, {
      conversation: collections.conversation,
      projectSnapshot: workspaceContext.snapshot
    });

    if (plan.mode === "delegate") {
      this.pendingDelegationApproval = {
        requestedAt: nowIso(),
        originalMessage: message,
        plan,
        projectSnapshot: workspaceContext.snapshot
      };
      const runContext = this.createStrategistRunContext(userMessage.id, { rootTask: null, childTasks: [] });
      this.strategistStreams.createStream(runContext.runId);
      this.strategistStreams.publish(runContext.runId, "run.started", {
        runId: runContext.runId,
        userMessageId: userMessage.id,
        rootTaskId: null,
        createdTaskIds: []
      });
      this.completeStrategistRun(
        runContext,
        buildDelegationApprovalPrompt(message, workspaceContext.snapshot),
        { mode: "approval_request" }
      );
      return {
        runId: runContext.runId,
        userMessageId: userMessage.id,
        createdTaskIds: [],
        rootTaskId: null
      };
    }

    const graph = materializeTaskGraph(plan);
    this.applyChatRoutingPreferences(graph, options);
    const runContext = this.createStrategistRunContext(userMessage.id, graph);

    this.strategistStreams.createStream(runContext.runId);
    this.strategistStreams.publish(runContext.runId, "run.started", {
      runId: runContext.runId,
      userMessageId: userMessage.id,
      rootTaskId: graph.rootTask?.id ?? null,
      createdTaskIds: runContext.createdTaskIds
    });

    this.persistDelegatedGraph(runContext, graph);
    if (this.options.autoSchedule && graph.rootTask) {
      await this.scheduleNow();
    }

    const shouldReuseStrategistSession =
      (!options?.runtime || this.strategistSessionRuntime === options.runtime) &&
      (!options?.model || this.strategistSessionModel === options.model);

    this.runStrategistReply(runContext, {
      message,
      fallbackReply: plan.reply,
      cwd: this.strategistChatCwd,
      capabilities: collections.capabilities,
      conversation: collections.conversation,
      projectSummary: summarizeWorkspaceForStrategist(workspaceContext.snapshot),
      sessionId: shouldReuseStrategistSession ? this.strategistSessionId : null,
      preferredRuntime: options?.runtime ?? null,
      preferredModel: options?.model ?? null
    });

    return {
      runId: runContext.runId,
      userMessageId: userMessage.id,
      createdTaskIds: runContext.createdTaskIds,
      rootTaskId: graph.rootTask?.id ?? null
    };
  }

  async retryTask(taskId: string): Promise<void> {
    const task = this.requireTask(taskId);
    await this.discardPreservedWorktree(taskId);
    const next: TaskRecord = {
      ...task,
      status: "ready",
      chosenRuntime: null,
      chosenProvider: null,
      chosenModel: null,
      routingRationale: null,
      updatedAt: nowIso()
    };
    this.store.upsertTask(next);
    this.releaseTaskLocks(taskId);
    this.store.insertReview(makeReview(taskId, "retry", "user", "Task scheduled for another attempt."));
    this.emitRefresh("task.retry");
    await this.scheduleNow();
  }

  async reassignTask(taskId: string, runtime?: RuntimeId | null, model?: string | null): Promise<void> {
    const task = this.requireTask(taskId);
    await this.discardPreservedWorktree(taskId);
    const next: TaskRecord = {
      ...task,
      status: "ready",
      preferredRuntime: runtime ?? task.preferredRuntime,
      chosenRuntime: null,
      chosenProvider: null,
      chosenModel: null,
      routingRationale: null,
      constraints:
        model && model.trim()
          ? { ...task.constraints, preferredModel: model.trim() }
          : Object.fromEntries(Object.entries(task.constraints).filter(([key]) => key !== "preferredModel")),
      updatedAt: nowIso()
    };
    this.store.upsertTask(next);
    this.store.insertReview(
      makeReview(taskId, "retry", "user", `Task reassigned${runtime ? ` with preferred runtime ${runtime}` : ""}.`)
    );
    this.emitRefresh("task.reassign");
    await this.scheduleNow();
  }

  async reopenTask(taskId: string): Promise<void> {
    const task = this.requireTask(taskId);
    await this.discardPreservedWorktree(taskId);
    const next: TaskRecord = {
      ...task,
      status: "ready",
      updatedAt: nowIso()
    };
    this.store.upsertTask(next);
    this.store.insertReview(makeReview(taskId, "reopen", "user", "Task reopened and returned to ready."));
    this.emitRefresh("task.reopen");
    await this.scheduleNow();
  }

  async approveTask(taskId: string): Promise<void> {
    this.mergeQueue = this.mergeQueue.then(async () => {
      const detail = await this.getTaskDetail(taskId);
      if (!detail) {
        throw new Error(`Task ${taskId} was not found`);
      }

      const task = detail.task;
      if (task.chosenRuntime === "codex-cloud" && !detail.worktree) {
        throw new Error("Codex Cloud approvals require explicit local diff application before approval in V1");
      }
      const lastJanitor =
        detail.janitorResults.length > 0 ? detail.janitorResults[detail.janitorResults.length - 1] : undefined;
      if (lastJanitor && lastJanitor.status === "failed") {
        throw new Error("Cannot approve a task with failing janitor results");
      }

      if (detail.worktree) {
        const [rootDirtyPaths, taskDirtyPaths] = await Promise.all([
          this.repoStatusPaths(this.options.repoRoot),
          this.repoStatusPaths(detail.worktree.path)
        ]);
        const overlappingDirtyPaths = rootDirtyPaths.filter((dirtyPath) =>
          taskDirtyPaths.some((taskPath) => taskPath === dirtyPath || taskPath.startsWith(`${dirtyPath}/`) || dirtyPath.startsWith(`${taskPath}/`))
        );
        if (overlappingDirtyPaths.length > 0) {
          throw new Error(
            `Repository has overlapping uncommitted changes on ${overlappingDirtyPaths.slice(0, 4).join(", ")}; merge is deferred until that overlap is clean`
          );
        }
      }

      if (detail.worktree) {
        const mergeResult = await runCommand("git", ["merge", "--no-ff", "--no-edit", detail.worktree.branchName], {
          cwd: this.options.repoRoot
        });
        if (!mergeResult.ok) {
          throw new Error(mergeResult.stderr || mergeResult.stdout || "merge failed");
        }
        const cleaned = await this.worktreeManager.cleanup(detail.worktree);
        this.store.upsertWorktree(cleaned);
      }

      this.releaseTaskLocks(taskId);
      const next: TaskRecord = {
        ...task,
        status: "done",
        updatedAt: nowIso()
      };
      this.store.upsertTask(next);
      this.store.insertReview(makeReview(taskId, "approve", "user", "Task approved for completion."));
      this.emitRefresh("task.approve");
      await this.scheduleNow();
    });

    return this.mergeQueue;
  }

  async rejectTask(taskId: string): Promise<void> {
    const task = this.requireTask(taskId);
    const next: TaskRecord = {
      ...task,
      status: "rejected",
      updatedAt: nowIso()
    };
    this.store.upsertTask(next);
    this.releaseTaskLocks(taskId);
    this.store.insertReview(makeReview(taskId, "reject", "user", "Task rejected and removed from the merge queue."));
    this.emitRefresh("task.reject");
  }

  async scheduleNow(options?: { force?: boolean }): Promise<void> {
    if (!this.options.autoSchedule && !options?.force) {
      return;
    }
    if (this.scheduling) {
      return;
    }
    this.scheduling = true;

    try {
      await this.refreshCapabilitySnapshots();
      this.promoteBacklogTasks();
      const collections = this.store.getCollections(this.goalId);
      const runnable = this.scheduler.selectRunnableTasks(collections.tasks, collections.sessions, collections.locks);
      for (const task of runnable) {
        if (this.activeRuns.has(task.id)) {
          continue;
        }
        this.activeRuns.set(task.id, {
          taskId: task.id,
          runId: "pending",
          sessionId: "pending"
        });
        void this.executeTask(task);
      }
    } finally {
      this.scheduling = false;
    }
  }

  private async seed(): Promise<void> {
    await this.refreshCapabilitySnapshots();
    const conversation = this.store.getCollections(this.goalId).conversation;
    if (conversation.messages.length === 0) {
      this.store.appendConversationMessage(this.goalId, {
        id: createId("msg"),
        role: "assistant",
        content:
          "Strategist ready. I will stay read-only by default, decompose work into routed tasks, and keep execution in delegated runtimes and worktrees.",
        createdAt: nowIso()
      });
    }
  }

  private async executeTask(task: TaskRecord): Promise<void> {
    const collections = this.store.getCollections(this.goalId);
    const activeSession = collections.sessions.find((session) => session.taskId === task.id) ?? null;
    const plan = this.router.routeTask(task, collections.capabilities, activeSession);
    const routedTask: TaskRecord = {
      ...task,
      status: "running",
      chosenRuntime: plan.runtime,
      chosenProvider: plan.provider,
      chosenModel: plan.model,
      tokenBudget: plan.tokenBudget,
      routingRationale: plan.rationale,
      attempts: task.attempts + 1,
      updatedAt: nowIso()
    };
    this.store.upsertTask(routedTask);
    this.store.insertEvent(makeEvent("task", routedTask.id, "task.started", {
      runtime: plan.runtime,
      provider: plan.provider,
      model: plan.model
    }));
    this.emitRefresh("task.running");

    let spawnResult;
    try {
      spawnResult = await this.spawner.spawnTask(routedTask, plan, buildExecutionPrompt(routedTask, plan));
    } catch (error) {
      await this.failTask(routedTask, error instanceof Error ? error.message : String(error));
      return;
    }

    this.store.upsertSession(spawnResult.session);
    this.store.upsertRun(spawnResult.run);
    if (spawnResult.worktree) {
      this.store.upsertWorktree(spawnResult.worktree);
    }
    if (spawnResult.logs.length > 0) {
      this.store.insertLogs(spawnResult.logs);
    }
    this.store.insertEvent(makeEvent("session", spawnResult.session.id, "session.started", {
      runtime: plan.runtime,
      provider: plan.provider,
      externalSessionId: spawnResult.session.externalSessionId
    }));
    this.store.insertEvent(makeEvent("run", spawnResult.run.id, "run.started", {
      runtime: plan.runtime,
      provider: plan.provider,
      attempt: spawnResult.run.attempt
    }));
    this.store.insertEvent(makeEvent("task", routedTask.id, "task.spawned", {
      runId: spawnResult.run.id,
      sessionId: spawnResult.session.id,
      runtime: plan.runtime,
      worktree: spawnResult.worktree?.path ?? null
    }));
    this.store.replaceAllLocks(this.lockManager.snapshot());
    this.activeRuns.set(routedTask.id, {
      taskId: routedTask.id,
      runId: spawnResult.run.id,
      sessionId: spawnResult.session.id
    });

    let watchdogCancelled = false;
    let watchdogReason: string | null = null;
    let transportErrorCount = 0;
    const handleWatchdogSignal = (message: string) => {
      if (!PROCESS_WATCHDOG_PATTERN.test(message)) {
        return;
      }
      transportErrorCount += 1;
      watchdogReason = summarizeWatchdogReason(message);
      if (transportErrorCount < PROCESS_WATCHDOG_ERROR_THRESHOLD || watchdogCancelled) {
        return;
      }
      watchdogCancelled = true;
      this.store.insertEvent(makeEvent("task", routedTask.id, "task.watchdog", {
        reason: watchdogReason,
        transportErrorCount
      }));
      this.emitRefresh("task.watchdog");
      void spawnResult.handle.cancel().catch(() => undefined);
    };

    for (const log of spawnResult.logs) {
      handleWatchdogSignal(log.message);
    }

    if (spawnResult.handle.process) {
      spawnResult.handle.process.child.stdout?.on("data", (chunk: Buffer | string) => {
        const text = chunk.toString();
        this.appendTaskLog(spawnResult.run.id, "stdout", text);
        handleWatchdogSignal(text);
      });
      spawnResult.handle.process.child.stderr?.on("data", (chunk: Buffer | string) => {
        const text = chunk.toString();
        this.appendTaskLog(spawnResult.run.id, "stderr", text);
        handleWatchdogSignal(text);
      });
    }

    const result = await spawnResult.handle.wait();
    this.activeRuns.delete(routedTask.id);

    if (result.stdout.trim() && spawnResult.handle.mode === "remote") {
      this.appendTaskLog(spawnResult.run.id, "stdout", result.stdout);
    }
    if (result.stderr.trim()) {
      this.appendTaskLog(spawnResult.run.id, "stderr", result.stderr);
    }

    const completedRun = {
      ...spawnResult.run,
      status: result.ok && !watchdogCancelled ? "complete" as const : "failed" as const,
      endedAt: nowIso(),
      exitCode: result.exitCode,
      summary:
        result.ok && !watchdogCancelled
          ? `Completed via ${plan.runtime}`
          : watchdogReason
            ? `Failed via ${plan.runtime}: ${watchdogReason}`
            : `Failed via ${plan.runtime}`
    };
    const completedSession = {
      ...spawnResult.session,
      status: result.ok && !watchdogCancelled ? "complete" as const : "failed" as const,
      updatedAt: nowIso()
    };
    this.store.upsertRun(completedRun);
    this.store.upsertSession(completedSession);
    this.store.insertEvent(makeEvent("run", completedRun.id, "run.completed", {
      runtime: plan.runtime,
      provider: plan.provider,
      status: completedRun.status,
      exitCode: completedRun.exitCode
    }));
    this.store.insertEvent(makeEvent("session", completedSession.id, "session.completed", {
      runtime: plan.runtime,
      provider: plan.provider,
      status: completedSession.status
    }));

    const janitorResult = await this.runJanitor(routedTask, spawnResult.worktree, completedRun.id);
    const finalTask = this.resolveTaskCompletion(routedTask, plan, result.ok && !watchdogCancelled, janitorResult);
    this.store.upsertTask(finalTask);
    if (finalTask.status !== "review") {
      this.releaseTaskLocks(finalTask.id);
    }
    if (spawnResult.worktree && finalTask.status !== "review") {
      const preserved =
        finalTask.status === "done"
          ? await this.worktreeManager.cleanup(spawnResult.worktree)
          : await this.worktreeManager.preserve(spawnResult.worktree);
      this.store.upsertWorktree(preserved);
    }

    this.store.insertEvent(makeEvent("task", finalTask.id, terminalTaskEventType(finalTask.status), {
      status: finalTask.status,
      runtime: finalTask.chosenRuntime,
      provider: finalTask.chosenProvider
    }));
    this.emitRefresh("task.completed");
    await this.scheduleNow();
  }

  private resolveTaskCompletion(
    task: TaskRecord,
    plan: ExecutionPlan,
    runSucceeded: boolean,
    janitorResult: JanitorResultRecord
  ): TaskRecord {
    let status: TaskRecord["status"];
    if (!runSucceeded) {
      status = "failed";
    } else if (janitorResult.status === "failed") {
      status = "blocked";
    } else if (plan.useWorktree || task.ownedFiles.length > 0) {
      status = "review";
    } else {
      status = "done";
    }

    return {
      ...task,
      status,
      updatedAt: nowIso()
    };
  }

  private async runJanitor(
    task: TaskRecord,
    worktree: Awaited<ReturnType<TaskSpawner["spawnTask"]>>["worktree"],
    runId: string
  ): Promise<JanitorResultRecord> {
    const checks = buildVerificationChecks(task);
    const result = await this.janitor.verifyTask(task, {
      repoRoot: this.options.repoRoot,
      worktree,
      checks
    });
    const enriched = {
      ...result,
      runId
    };
    this.store.insertJanitorResult(enriched);
    return enriched;
  }

  private promoteBacklogTasks(): void {
    const collections = this.store.getCollections(this.goalId);
    const completed = new Set(collections.tasks.filter((task) => task.status === "done").map((task) => task.id));
    const toPromote = collections.tasks.filter(
      (task) => task.status === "backlog" && task.dependencies.every((dependency) => completed.has(dependency))
    );

    for (const task of toPromote) {
      this.store.upsertTask({
        ...task,
        status: "ready",
        updatedAt: nowIso()
      });
    }
  }

  private appendTaskLog(runId: string, stream: LogRecord["stream"], message: string): void {
    const log: LogRecord = {
      id: createId("log"),
      runId,
      stream,
      message,
      createdAt: nowIso()
    };
    this.store.insertLogs([log]);
    this.emitRefresh("log.appended");
  }

  private async failTask(task: TaskRecord, reason: string): Promise<void> {
    this.activeRuns.delete(task.id);
    const failed: TaskRecord = {
      ...task,
      status: "failed",
      updatedAt: nowIso()
    };
    this.store.upsertTask(failed);
    this.store.insertEvent(makeEvent("task", task.id, "task.failed", { reason }));
    this.releaseTaskLocks(task.id);
    this.emitRefresh("task.failed");
  }

  private releaseTaskLocks(taskId: string): void {
    this.lockManager.releaseForTask(taskId);
    this.store.replaceAllLocks(this.lockManager.snapshot());
  }

  private async discardPreservedWorktree(taskId: string): Promise<void> {
    const worktree = this.store.getCollections(this.goalId).worktrees.find((entry) => entry.taskId === taskId);
    if (!worktree || worktree.status !== "preserved") {
      return;
    }
    const cleaned = await this.worktreeManager.cleanup(worktree);
    this.store.upsertWorktree(cleaned);
  }

  private requireTask(taskId: string): TaskRecord {
    const task = this.store.getTask(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} was not found`);
    }
    return task;
  }

  private async getTaskDiff(taskId: string): Promise<string> {
    const detail = buildTaskDetailPayload(this.store.getCollections(this.goalId), taskId, "");
    if (!detail) {
      return "";
    }
    const cwd = detail.worktree?.path ?? this.options.repoRoot;
    const result = await runCommand("git", ["diff", "--no-ext-diff"], { cwd });
    return `${result.stdout}${result.stderr}`.trim();
  }

  private async repoStatusPaths(cwd: string): Promise<string[]> {
    const result = await runCommand("git", ["status", "--porcelain"], { cwd });
    if (!result.ok || !result.stdout.trim()) {
      return [];
    }
    return result.stdout
      .split("\n")
      .map((line) => line.trimEnd())
      .filter((line) => line.length > 3)
      .map((line) => line.slice(3).trim())
      .filter((line) => line.length > 0);
  }

  private createStrategistRunContext(
    userMessageId: string,
    graph: ReturnType<typeof materializeTaskGraph>
  ): StrategistRunContext {
    return {
      runId: createId("chatrun"),
      userMessageId,
      createdTaskIds: graph.rootTask ? [graph.rootTask.id, ...graph.childTasks.map((task) => task.id)] : [],
      rootTaskId: graph.rootTask?.id ?? null
    };
  }

  private persistDelegatedGraph(
    runContext: StrategistRunContext,
    graph: ReturnType<typeof materializeTaskGraph>
  ): void {
    if (!graph.rootTask) {
      return;
    }
    this.store.upsertTask(graph.rootTask);
    this.store.bulkUpsertTasks(graph.childTasks);
    this.store.insertEvent(makeEvent("task", graph.rootTask.id, "strategist.planned", {
      rootTaskId: graph.rootTask.id,
      childTaskIds: graph.childTasks.map((task) => task.id)
    }));
    this.strategistStreams.publish(runContext.runId, "task.spawned", {
      runId: runContext.runId,
      rootTaskId: graph.rootTask.id,
      createdTaskIds: runContext.createdTaskIds
    });
    this.emitRefresh("strategist");
  }

  private applyChatRoutingPreferences(
    graph: ReturnType<typeof materializeTaskGraph>,
    options?: { runtime?: "codex-local" | "opencode" | null; model?: string | null }
  ): void {
    const preferredRuntime = options?.runtime ?? null;
    if (!preferredRuntime) {
      return;
    }
    const preferredProvider = runtimeToPreferredProvider(preferredRuntime);
    const preferredModel = options?.model?.trim() ? options.model.trim() : null;
    const apply = (task: TaskRecord | null) => {
      if (!task || !isSuitablePreferredRuntime(task, preferredRuntime)) {
        return task;
      }
      task.preferredRuntime = preferredRuntime;
      task.preferredProvider = preferredProvider;
      if (preferredModel) {
        task.constraints = {
          ...task.constraints,
          preferredModel
        };
      }
      return task;
    };

    apply(graph.rootTask);
    for (const task of graph.childTasks) {
      apply(task);
    }
  }

  private completeStrategistRun(
    runContext: StrategistRunContext,
    reply: string,
    metadata?: Record<string, unknown>
  ): void {
    this.store.appendConversationMessage(this.goalId, {
      id: createId("msg"),
      role: "assistant",
      content: reply,
      createdAt: nowIso()
    });
    this.strategistStreams.publish(runContext.runId, "assistant.completed", {
      runId: runContext.runId,
      reply,
      rootTaskId: runContext.rootTaskId,
      createdTaskIds: runContext.createdTaskIds,
      ...(metadata ?? {})
    });
    this.strategistStreams.end(runContext.runId);
    this.emitRefresh("strategist.completed");
  }

  private runStrategistReply(
    runContext: StrategistRunContext,
    input: {
      message: string;
      fallbackReply: string;
      cwd: string;
      capabilities: ReturnType<OrchestratorStore["getCollections"]>["capabilities"];
      conversation: ReturnType<OrchestratorStore["getCollections"]>["conversation"];
      projectSummary?: string | null;
      sessionId?: string | null;
      preferredRuntime?: "codex-local" | "opencode" | null;
      preferredModel?: string | null;
    }
  ): void {
    if (shouldBypassNativeStrategist(input.message, runContext.createdTaskIds.length > 0)) {
      const deterministicReply = buildDeterministicChatReply(input.message, input.fallbackReply);
      this.completeStrategistRun(runContext, deterministicReply, {
        mode: "deterministic"
      });
      return;
    }

    let reply = "";
    const complete = (finalReply: string) => {
      reply = finalReply;
      this.completeStrategistRun(runContext, finalReply);
    };

    this.strategistRuntime.run(input, {
      onSessionStarted: (sessionId) => {
        this.strategistSessionId = sessionId;
        this.strategistSessionRuntime = input.preferredRuntime ?? "opencode";
        this.strategistSessionModel = input.preferredModel ?? null;
      },
      onDelta: (delta) => {
        reply += delta;
        this.strategistStreams.publish(runContext.runId, "assistant.delta", {
          runId: runContext.runId,
          delta,
          reply
        });
      },
      onComplete: complete,
      onError: (message) => {
        const fallbackReply = reply.trim() || input.fallbackReply;
        this.strategistStreams.publish(runContext.runId, "run.failed", {
          runId: runContext.runId,
          error: message,
          reply: fallbackReply
        });
        complete(fallbackReply);
      }
    });
  }

  private emitRefresh(reason: string): void {
    this.emit("refresh", {
      reason,
      timestamp: nowIso()
    });
  }
}

function summarizeWorkspaceForStrategist(snapshot: ProjectSnapshot | null): string | null {
  if (!snapshot) {
    return null;
  }
  const activeProject =
    snapshot.activeRoot?.name ??
    snapshot.projects[0]?.name ??
    "workspace";
  const evidence = snapshot.evidenceMatches.slice(0, 3).map((match) => match.path);
  const runtimeSummary = snapshot.runtimeHealth?.filter((runtime) => runtime.status === "ready").map((runtime) => runtime.runtime) ?? [];
  return [
    `Active project: ${activeProject}.`,
    evidence.length > 0 ? `Relevant files: ${evidence.join(", ")}.` : null,
    `Operational health: ${snapshot.operationalHealth.runningTasks} running, ${snapshot.operationalHealth.reviewTasks} in review, ${snapshot.operationalHealth.failedTasks} failed.`,
    runtimeSummary.length > 0 ? `Ready runtimes: ${runtimeSummary.join(", ")}.` : null
  ]
    .filter((line): line is string => Boolean(line))
    .join(" ");
}

function shouldBypassNativeStrategist(message: string, hasDelegatedWork: boolean): boolean {
  if (hasDelegatedWork) {
    return false;
  }
  const normalized = message.trim().toLowerCase();
  return /^(hi|hello|hey|yo|sup|how are you|how r u|wyd|thanks|thank you|ok|okay)\b/.test(normalized) || normalized.length <= 2;
}

function buildDeterministicChatReply(message: string, fallbackReply: string): string {
  const normalized = message.trim().toLowerCase();
  if (/^(hi|hello|hey|yo|sup)\b/.test(normalized)) {
    return "Hi. Talk to me normally here. If something needs real execution, I'll start it and show progress as it begins.";
  }
  if (/^(how are you|how r u|wyd)\b/.test(normalized)) {
    return "I’m here and ready. Ask a question, describe a goal, or tell me what you want done.";
  }
  if (/^(thanks|thank you|ok|okay)\b/.test(normalized)) {
    return "Understood.";
  }
  if (normalized.length <= 2) {
    return "Need a bit more than that. Ask a question or describe the goal and I’ll handle it from there.";
  }
  return fallbackReply;
}

function classifyDelegationApprovalResponse(message: string): "approve" | "decline" | null {
  const normalized = message.trim().toLowerCase();
  if (/^(yes|yep|yeah|sure|ok|okay|do it|go ahead|proceed|spawn it|create it|run it)\b/.test(normalized)) {
    return "approve";
  }
  if (/^(no|nope|nah|don'?t|do not|stop|cancel|not now)\b/.test(normalized)) {
    return "decline";
  }
  return null;
}

function buildDelegationApprovalPrompt(message: string, snapshot: ProjectSnapshot | null): string {
  const activeRoot = snapshot?.activeRoot?.name ?? snapshot?.projects[0]?.name ?? "the workspace";
  const conciseGoal = message.trim().replace(/\s+/g, " ");
  return `I can handle "${conciseGoal}" in ${activeRoot}. That would start execution. Do you want me to proceed?`;
}

function buildDelegationAcceptedReply(message: string, snapshot: ProjectSnapshot | null): string {
  const activeRoot = snapshot?.activeRoot?.name ?? snapshot?.projects[0]?.name ?? "the workspace";
  const conciseGoal = message.trim().replace(/\s+/g, " ");
  return `Starting work on "${conciseGoal}" in ${activeRoot} now.`;
}

function makeEvent(
  entityType: EventRecord["entityType"],
  entityId: string,
  eventType: string,
  payload: EventRecord["payload"]
): EventRecord {
  return {
    id: createId("evt"),
    entityType,
    entityId,
    eventType,
    payload,
    createdAt: nowIso()
  };
}

function makeReview(
  taskId: string,
  decision: ReviewDecisionRecord["decision"],
  reviewer: string,
  summary: string
): ReviewDecisionRecord {
  return {
    id: createId("review"),
    taskId,
    decision,
    reviewer,
    summary,
    createdAt: nowIso()
  };
}

function buildVerificationChecks(task: TaskRecord): JanitorCheckDefinition[] {
  return task.verificationPolicy.map((type) => {
    switch (type) {
      case "typecheck":
        return { type, label: "Typecheck", command: "cd agent-orchestrator && npm run build:server" };
      case "test":
        return { type, label: "Tests", command: "cd agent-orchestrator && npm run test" };
      case "build":
        return { type, label: "Build", command: "cd agent-orchestrator && npm run build" };
      case "review":
        return { type, label: "Review", command: "git diff --stat" };
      default:
        return { type, label: type };
    }
  });
}

function buildExecutionPrompt(task: TaskRecord, plan: ExecutionPlan): string {
  const directives = [
    "You are executing a delegated task inside a deterministic orchestrator.",
    "Do not broaden scope beyond the declared task.",
    "Prefer concise progress notes and leave a clear summary for review.",
    plan.useWorktree ? "You are in a write-isolated worktree." : "This is a read-only or non-worktree task."
  ];
  return `${directives.join("\n")}\n\n${task.description}`;
}

const PROCESS_WATCHDOG_PATTERN =
  /failed to connect to websocket|failed to lookup address information|stream disconnected before completion|reconnecting\.\.\./i;
const PROCESS_WATCHDOG_ERROR_THRESHOLD = 3;

function terminalTaskEventType(status: TaskRecord["status"]): string {
  switch (status) {
    case "failed":
      return "task.failed";
    case "blocked":
      return "task.blocked";
    case "rejected":
      return "task.rejected";
    default:
      return "task.completed";
  }
}

function summarizeWatchdogReason(message: string): string {
  const normalized = message.replace(/\s+/g, " ").trim();
  if (normalized.length <= 180) {
    return normalized;
  }
  return `${normalized.slice(0, 177).trim()}...`;
}

function runtimeToPreferredProvider(runtime: "codex-local" | "opencode"): ProviderId {
  return runtime === "codex-local" ? "openai" : "opencode";
}

function isSuitablePreferredRuntime(task: TaskRecord, runtime: "codex-local" | "opencode"): boolean {
  if (!task.runtimeCandidates.includes(runtime)) {
    return false;
  }
  const fit = {
    planning: { "codex-local": 72, opencode: 80 },
    explore: { "codex-local": 68, opencode: 76 },
    implement: { "codex-local": 90, opencode: 82 },
    refactor: { "codex-local": 88, opencode: 78 },
    "test-fix": { "codex-local": 87, opencode: 80 },
    review: { "codex-local": 76, opencode: 72 },
    docs: { "codex-local": 64, opencode: 70 },
    verify: { "codex-local": 85, opencode: 68 },
    merge: { "codex-local": 82, opencode: 50 }
  } satisfies Record<TaskRecord["taskType"], Record<"codex-local" | "opencode", number>>;
  return fit[task.taskType][runtime] >= 72;
}
