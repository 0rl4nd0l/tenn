import fs from "fs";
import path from "path";
import initSqlJs, { type Database as SqlJsDatabase, type SqlJsStatic } from "sql.js";

import type {
  BoardState,
  CreateTaskGraphInput,
  CreateTaskInput,
  DashboardStats,
  EventRecord,
  HeadroomBand,
  JanitorResultRecord,
  LogRecord,
  OwnershipLockRecord,
  ProviderCapabilitySnapshot,
  ReviewDecisionRecord,
  RunRecord,
  SessionRecord,
  StrategistConversation,
  StrategistMessage,
  TaskDetailPayload,
  TaskRecord,
  WorktreeRecord
} from "../../shared/types";
import { DEFAULT_TOKEN_BUDGET } from "../../shared/types";
import { ensureDir } from "../utils/filesystem";
import { makeId } from "../utils/id";
import { safeParseJson, toJson } from "../utils/json";
import { nowIso } from "../utils/time";
import { SCHEMA_STATEMENTS } from "./schema";

type SqlRow = Record<string, unknown>;
type SqlExecResult = {
  columns: string[];
  values: unknown[][];
};

export interface StoreCollections {
  tasks: TaskRecord[];
  sessions: SessionRecord[];
  runs: RunRecord[];
  events: EventRecord[];
  logs: LogRecord[];
  janitorResults: JanitorResultRecord[];
  reviews: ReviewDecisionRecord[];
  locks: OwnershipLockRecord[];
  worktrees: WorktreeRecord[];
  capabilities: ProviderCapabilitySnapshot[];
  conversation: StrategistConversation;
}

const EMPTY_STATS: DashboardStats = {
  queue: {
    readyTasks: 0,
    runningTasks: 0,
    reviewTasks: 0,
    blockedTasks: 0,
    mergeQueueDepth: 0
  },
  tokenBands: {
    healthy: 0,
    caution: 0,
    compact_or_fork: 0,
    migrate: 0,
    hard_stop: 0
  },
  runtimeLoad: {
    "codex-local": 0,
    "codex-cloud": 0,
    claude: 0,
    gemini: 0,
    cursor: 0,
    opencode: 0,
    generic: 0
  }
};

function q(value: unknown): string {
  if (value === null || value === undefined) {
    return "NULL";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : "NULL";
  }
  if (typeof value === "boolean") {
    return value ? "1" : "0";
  }
  return `'${String(value).replace(/'/g, "''")}'`;
}

function asTask(row: SqlRow): TaskRecord {
  return {
    id: String(row.id),
    goalId: String(row.goal_id),
    parentId: row.parent_id ? String(row.parent_id) : null,
    title: String(row.title),
    description: String(row.description),
    status: row.status as TaskRecord["status"],
    role: row.role as TaskRecord["role"],
    taskType: row.task_type as TaskRecord["taskType"],
    agentMode: row.agent_mode as TaskRecord["agentMode"],
    delegationPolicy: row.delegation_policy as TaskRecord["delegationPolicy"],
    locality: row.locality as TaskRecord["locality"],
    runtimeCandidates: safeParseJson(String(row.runtime_candidates), []),
    providerCandidates: safeParseJson(String(row.provider_candidates), []),
    preferredRuntime: row.preferred_runtime ? (String(row.preferred_runtime) as TaskRecord["preferredRuntime"]) : null,
    preferredProvider: row.preferred_provider ? (String(row.preferred_provider) as TaskRecord["preferredProvider"]) : null,
    chosenRuntime: row.chosen_runtime ? (String(row.chosen_runtime) as TaskRecord["chosenRuntime"]) : null,
    chosenProvider: row.chosen_provider ? (String(row.chosen_provider) as TaskRecord["chosenProvider"]) : null,
    chosenModel: row.chosen_model ? String(row.chosen_model) : null,
    ownedFiles: safeParseJson(String(row.owned_files), []),
    readOnlyPaths: safeParseJson(String(row.read_only_paths), []),
    verificationPolicy: safeParseJson(String(row.verification_policy), []),
    tokenBudget: safeParseJson(String(row.token_budget), DEFAULT_TOKEN_BUDGET),
    dependencies: safeParseJson(String(row.dependencies), []),
    attempts: Number(row.attempts),
    maxAttempts: Number(row.max_attempts),
    routingRationale: row.routing_rationale ? safeParseJson(String(row.routing_rationale), null) : null,
    constraints: safeParseJson(String(row.constraints), {}),
    createdAt: String(row.created_at),
    updatedAt: String(row.updated_at)
  };
}

function asSession(row: SqlRow): SessionRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    runtime: row.runtime as SessionRecord["runtime"],
    provider: row.provider as SessionRecord["provider"],
    model: String(row.model),
    mode: row.mode as SessionRecord["mode"],
    localOrCloud: row.local_or_cloud as SessionRecord["localOrCloud"],
    nativeStatsSupported: Boolean(Number(row.native_stats_supported ?? 0)),
    exactUsageSupported: Boolean(Number(row.exact_usage_supported ?? 0)),
    compactionSupported: Boolean(Number(row.compaction_supported ?? 0)),
    contextWindow: Number(row.context_window),
    maxOutputTokens: Number(row.max_output_tokens),
    estimatedContextUsed: Number(row.estimated_context_used),
    nativeContextUsed: row.native_context_used === null || row.native_context_used === undefined ? null : Number(row.native_context_used),
    headroom: Number(row.headroom),
    quotaState: row.quota_state as SessionRecord["quotaState"],
    status: row.status as SessionRecord["status"],
    externalSessionId: row.external_session_id ? String(row.external_session_id) : null,
    startedAt: String(row.started_at),
    updatedAt: String(row.updated_at)
  };
}

function asRun(row: SqlRow): RunRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    sessionId: row.session_id ? String(row.session_id) : null,
    attempt: Number(row.attempt),
    status: row.status as RunRecord["status"],
    startedAt: String(row.started_at),
    endedAt: row.ended_at ? String(row.ended_at) : null,
    exitCode: row.exit_code === null || row.exit_code === undefined ? null : Number(row.exit_code),
    summary: String(row.summary)
  };
}

function asEvent(row: SqlRow): EventRecord {
  return {
    id: String(row.id),
    entityType: row.entity_type as EventRecord["entityType"],
    entityId: String(row.entity_id),
    eventType: String(row.event_type),
    payload: safeParseJson(String(row.payload), null),
    createdAt: String(row.created_at)
  };
}

function asLog(row: SqlRow): LogRecord {
  return {
    id: String(row.id),
    runId: String(row.run_id),
    stream: row.stream as LogRecord["stream"],
    message: String(row.message),
    createdAt: String(row.created_at)
  };
}

function asJanitor(row: SqlRow): JanitorResultRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    runId: row.run_id ? String(row.run_id) : null,
    status: row.status as JanitorResultRecord["status"],
    checks: safeParseJson(String(row.checks), []),
    diffSummary: String(row.diff_summary),
    createdAt: String(row.created_at)
  };
}

function asReview(row: SqlRow): ReviewDecisionRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    decision: row.decision as ReviewDecisionRecord["decision"],
    reviewer: String(row.reviewer),
    summary: String(row.summary),
    createdAt: String(row.created_at)
  };
}

function asLock(row: SqlRow): OwnershipLockRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    pathGlob: String(row.path_glob),
    mode: row.mode as OwnershipLockRecord["mode"],
    status: row.status as OwnershipLockRecord["status"],
    createdAt: String(row.created_at),
    updatedAt: String(row.updated_at)
  };
}

function asWorktree(row: SqlRow): WorktreeRecord {
  return {
    id: String(row.id),
    taskId: String(row.task_id),
    branchName: String(row.branch_name),
    path: String(row.path),
    baseRef: String(row.base_ref),
    status: row.status as WorktreeRecord["status"],
    createdAt: String(row.created_at),
    updatedAt: String(row.updated_at)
  };
}

function computeStats(board: Omit<BoardState, "stats">): DashboardStats {
  const stats: DashboardStats = JSON.parse(JSON.stringify(EMPTY_STATS));
  for (const task of board.tasks) {
    stats.tokenBands[task.tokenBudget.headroomBand as HeadroomBand] += 1;
    if (task.status === "ready") stats.queue.readyTasks += 1;
    if (task.status === "running") stats.queue.runningTasks += 1;
    if (task.status === "review") stats.queue.reviewTasks += 1;
    if (task.status === "blocked") stats.queue.blockedTasks += 1;
    if (task.taskType === "merge" && task.status !== "done") stats.queue.mergeQueueDepth += 1;
  }
  for (const session of board.sessions) {
    if (session.status === "running") {
      stats.runtimeLoad[session.runtime] += 1;
    }
  }
  return stats;
}

export class OrchestratorStore {
  private static sqlJs: Promise<SqlJsStatic> | null = null;

  private constructor(
    private readonly filePath: string,
    private readonly database: SqlJsDatabase
  ) {
    ensureDir(path.dirname(filePath));
    for (const statement of SCHEMA_STATEMENTS) {
      this.exec(statement);
    }
  }

  static async open(filePath: string): Promise<OrchestratorStore> {
    ensureDir(path.dirname(filePath));
    const sql = await this.loadSqlJs();
    const existing = fs.existsSync(filePath) ? fs.readFileSync(filePath) : undefined;
    const database = new sql.Database(existing ? new Uint8Array(existing) : undefined);
    return new OrchestratorStore(filePath, database);
  }

  private static loadSqlJs(): Promise<SqlJsStatic> {
    if (!this.sqlJs) {
      this.sqlJs = initSqlJs({
        locateFile: (file) => path.join(path.dirname(require.resolve("sql.js")), file)
      });
    }
    return this.sqlJs;
  }

  close(): void {
    this.flush();
    this.database.close();
  }

  destroy(): void {
    this.close();
  }

  private exec(sql: string): string {
    this.database.run(sql);
    this.flush();
    return "";
  }

  private query(sql: string): SqlRow[] {
    const [result] = this.database.exec(sql) as SqlExecResult[];
    if (!result) {
      return [];
    }
    return result.values.map((values) =>
      Object.fromEntries(result.columns.map((column, index) => [column, values[index] ?? null]))
    );
  }

  private first(sql: string): SqlRow | null {
    return this.query(sql)[0] ?? null;
  }

  private flush(): void {
    fs.writeFileSync(this.filePath, Buffer.from(this.database.export()));
  }

  listTasks(goalId: string): TaskRecord[] {
    return this.query(`SELECT * FROM tasks WHERE goal_id = ${q(goalId)} ORDER BY created_at ASC`).map(asTask);
  }

  getTask(taskId: string): TaskRecord | null {
    const row = this.first(`SELECT * FROM tasks WHERE id = ${q(taskId)} LIMIT 1`);
    return row ? asTask(row) : null;
  }

  createTask(input: CreateTaskInput): TaskRecord {
    const now = nowIso();
    const task: TaskRecord = {
      id: makeId("task"),
      goalId: input.goalId,
      parentId: input.parentId ?? null,
      title: input.title,
      description: input.description,
      status: input.status ?? "backlog",
      role: input.role,
      taskType: input.taskType,
      agentMode: input.agentMode ?? (input.role === "strategist" ? "read_only_strategist" : "single"),
      delegationPolicy: input.delegationPolicy ?? "orchestrator_subtasks",
      locality: input.locality ?? "local",
      runtimeCandidates: input.runtimeCandidates ?? ["codex-local", "codex-cloud", "claude", "gemini", "cursor", "opencode", "generic"],
      providerCandidates: input.providerCandidates ?? ["openai", "anthropic", "google", "cursor", "opencode", "generic"],
      preferredRuntime: input.preferredRuntime ?? null,
      preferredProvider: input.preferredProvider ?? null,
      chosenRuntime: null,
      chosenProvider: null,
      chosenModel: null,
      ownedFiles: input.ownedFiles ?? [],
      readOnlyPaths: input.readOnlyPaths ?? [],
      verificationPolicy: input.verificationPolicy ?? ["diff_sanity", "owned_file_boundary"],
      tokenBudget: { ...DEFAULT_TOKEN_BUDGET, ...(input.tokenBudget ?? {}) },
      dependencies: input.dependencies ?? [],
      attempts: 0,
      maxAttempts: 3,
      routingRationale: null,
      constraints: input.constraints ?? {},
      createdAt: now,
      updatedAt: now
    };
    this.upsertTask(task);
    return task;
  }

  createTaskGraph(input: CreateTaskGraphInput): TaskRecord[] {
    const localKeyToId = new Map<string, string>();
    const created: TaskRecord[] = [];
    for (const node of input.tasks) {
      const task = this.createTask({
        ...node,
        goalId: input.goalId,
        parentId: input.parentId
      });
      localKeyToId.set(node.localKey, task.id);
      created.push(task);
    }
    for (const node of input.tasks) {
      if (!node.dependsOnLocalKeys?.length) continue;
      const task = created.find((candidate) => candidate.title === node.title && candidate.description === node.description);
      if (!task) continue;
      const dependencies = node.dependsOnLocalKeys
        .map((key) => localKeyToId.get(key))
        .filter((value): value is string => Boolean(value));
      this.updateTask(task.id, {
        dependencies,
        status: dependencies.length > 0 && task.status === "ready" ? "backlog" : task.status
      });
    }
    return created.map((task) => this.getTask(task.id) ?? task);
  }

  upsertTask(task: TaskRecord): void {
    this.exec(`DELETE FROM tasks WHERE id = ${q(task.id)};
      INSERT INTO tasks (
        id, goal_id, parent_id, title, description, status, role, task_type, agent_mode,
        delegation_policy, locality, runtime_candidates, provider_candidates, preferred_runtime,
        preferred_provider, chosen_runtime, chosen_provider, chosen_model, owned_files,
        read_only_paths, verification_policy, token_budget, dependencies, attempts, max_attempts,
        routing_rationale, constraints, created_at, updated_at
      ) VALUES (
        ${q(task.id)}, ${q(task.goalId)}, ${q(task.parentId)}, ${q(task.title)}, ${q(task.description)}, ${q(task.status)},
        ${q(task.role)}, ${q(task.taskType)}, ${q(task.agentMode)}, ${q(task.delegationPolicy)}, ${q(task.locality)},
        ${q(toJson(task.runtimeCandidates))}, ${q(toJson(task.providerCandidates))}, ${q(task.preferredRuntime)},
        ${q(task.preferredProvider)}, ${q(task.chosenRuntime)}, ${q(task.chosenProvider)}, ${q(task.chosenModel)},
        ${q(toJson(task.ownedFiles))}, ${q(toJson(task.readOnlyPaths))}, ${q(toJson(task.verificationPolicy))},
        ${q(toJson(task.tokenBudget))}, ${q(toJson(task.dependencies))}, ${q(task.attempts)}, ${q(task.maxAttempts)},
        ${q(task.routingRationale ? toJson(task.routingRationale) : null)}, ${q(toJson(task.constraints))},
        ${q(task.createdAt)}, ${q(task.updatedAt)}
      );`);
  }

  bulkUpsertTasks(tasks: TaskRecord[]): void {
    for (const task of tasks) {
      this.upsertTask(task);
    }
  }

  updateTask(taskId: string, patch: Partial<TaskRecord>): TaskRecord {
    const current = this.getTask(taskId);
    if (!current) throw new Error(`Task ${taskId} not found`);
    const next = { ...current, ...patch, updatedAt: nowIso() };
    this.upsertTask(next);
    return next;
  }

  addMessage(goalId: string, role: StrategistMessage["role"], content: string): StrategistMessage {
    const message: StrategistMessage = { id: makeId("msg"), role, content, createdAt: nowIso() };
    this.appendConversationMessage(goalId, message);
    return message;
  }

  appendConversationMessage(goalId: string, message: StrategistMessage): void {
    this.exec(
      `INSERT INTO conversation_messages (id, goal_id, role, content, created_at) VALUES (${q(message.id)}, ${q(goalId)}, ${q(message.role)}, ${q(message.content)}, ${q(message.createdAt)});`
    );
  }

  getConversation(goalId: string): StrategistConversation {
    const messages = this.query(
      `SELECT * FROM conversation_messages WHERE goal_id = ${q(goalId)} ORDER BY created_at ASC`
    ).map(
      (row): StrategistMessage => ({
        id: String(row.id),
        role: row.role as StrategistMessage["role"],
        content: String(row.content),
        createdAt: String(row.created_at)
      })
    );
    const latestPlan = this.first(
      `SELECT id FROM tasks WHERE goal_id = ${q(goalId)} AND task_type = 'planning' ORDER BY created_at DESC LIMIT 1`
    );
    return { messages, latestPlanTaskId: latestPlan ? String(latestPlan.id) : null };
  }

  listSessions(): SessionRecord[] {
    return this.query(`SELECT * FROM sessions ORDER BY started_at ASC`).map(asSession);
  }

  getSessionByTask(taskId: string): SessionRecord | null {
    return this.listSessions().find((session) => session.taskId === taskId) ?? null;
  }

  createSession(session: SessionRecord): SessionRecord {
    this.upsertSession(session);
    return session;
  }

  upsertSession(session: SessionRecord): SessionRecord {
    this.exec(`DELETE FROM sessions WHERE id = ${q(session.id)};
      INSERT INTO sessions (
        id, task_id, runtime, provider, model, mode, local_or_cloud, native_stats_supported,
        exact_usage_supported, compaction_supported, context_window, max_output_tokens,
        estimated_context_used, native_context_used, headroom, quota_state, status,
        external_session_id, started_at, updated_at
      ) VALUES (
        ${q(session.id)}, ${q(session.taskId)}, ${q(session.runtime)}, ${q(session.provider)}, ${q(session.model)}, ${q(session.mode)},
        ${q(session.localOrCloud)}, ${q(session.nativeStatsSupported ? 1 : 0)}, ${q(session.exactUsageSupported ? 1 : 0)},
        ${q(session.compactionSupported ? 1 : 0)}, ${q(session.contextWindow)}, ${q(session.maxOutputTokens)},
        ${q(session.estimatedContextUsed)}, ${q(session.nativeContextUsed)}, ${q(session.headroom)}, ${q(session.quotaState)},
        ${q(session.status)}, ${q(session.externalSessionId)}, ${q(session.startedAt)}, ${q(session.updatedAt)}
      );`);
    return session;
  }

  updateSession(sessionId: string, patch: Partial<SessionRecord>): SessionRecord {
    const current = this.listSessions().find((session) => session.id === sessionId);
    if (!current) throw new Error(`Session ${sessionId} not found`);
    const next = { ...current, ...patch, updatedAt: nowIso() };
    return this.upsertSession(next);
  }

  listRuns(taskId?: string): RunRecord[] {
    return this.query(
      taskId ? `SELECT * FROM runs WHERE task_id = ${q(taskId)} ORDER BY started_at ASC` : `SELECT * FROM runs ORDER BY started_at ASC`
    ).map(asRun);
  }

  createRun(run: RunRecord): RunRecord {
    this.upsertRun(run);
    return run;
  }

  upsertRun(run: RunRecord): RunRecord {
    this.exec(`DELETE FROM runs WHERE id = ${q(run.id)};
      INSERT INTO runs (id, task_id, session_id, attempt, status, started_at, ended_at, exit_code, summary)
      VALUES (${q(run.id)}, ${q(run.taskId)}, ${q(run.sessionId)}, ${q(run.attempt)}, ${q(run.status)}, ${q(run.startedAt)}, ${q(run.endedAt)}, ${q(run.exitCode)}, ${q(run.summary)});`);
    return run;
  }

  updateRun(runId: string, patch: Partial<RunRecord>): RunRecord {
    const current = this.listRuns().find((run) => run.id === runId);
    if (!current) throw new Error(`Run ${runId} not found`);
    return this.upsertRun({ ...current, ...patch });
  }

  listLogs(taskId?: string): LogRecord[] {
    return this.query(
      taskId
        ? `SELECT logs.* FROM logs INNER JOIN runs ON runs.id = logs.run_id WHERE runs.task_id = ${q(taskId)} ORDER BY logs.created_at ASC`
        : `SELECT * FROM logs ORDER BY created_at ASC`
    ).map(asLog);
  }

  addLog(runId: string, stream: LogRecord["stream"], message: string): LogRecord {
    const log: LogRecord = { id: makeId("log"), runId, stream, message, createdAt: nowIso() };
    this.insertLogs([log]);
    return log;
  }

  insertLogs(logs: LogRecord[]): void {
    for (const log of logs) {
      this.exec(
        `INSERT INTO logs (id, run_id, stream, message, created_at) VALUES (${q(log.id)}, ${q(log.runId)}, ${q(log.stream)}, ${q(log.message)}, ${q(log.createdAt)});`
      );
    }
  }

  listEvents(): EventRecord[] {
    return this.query(`SELECT * FROM events ORDER BY created_at ASC`).map(asEvent);
  }

  insertEvent(event: EventRecord): void {
    this.exec(
      `INSERT INTO events (id, entity_type, entity_id, event_type, payload, created_at) VALUES (${q(event.id)}, ${q(event.entityType)}, ${q(event.entityId)}, ${q(event.eventType)}, ${q(toJson(event.payload))}, ${q(event.createdAt)});`
    );
  }

  addJanitorResult(result: JanitorResultRecord): JanitorResultRecord {
    this.insertJanitorResult(result);
    return result;
  }

  insertJanitorResult(result: JanitorResultRecord): void {
    this.exec(
      `INSERT INTO janitor_results (id, task_id, run_id, status, checks, diff_summary, created_at) VALUES (${q(result.id)}, ${q(result.taskId)}, ${q(result.runId)}, ${q(result.status)}, ${q(toJson(result.checks))}, ${q(result.diffSummary)}, ${q(result.createdAt)});`
    );
  }

  listJanitorResults(taskId?: string): JanitorResultRecord[] {
    return this.query(
      taskId
        ? `SELECT * FROM janitor_results WHERE task_id = ${q(taskId)} ORDER BY created_at ASC`
        : `SELECT * FROM janitor_results ORDER BY created_at ASC`
    ).map(asJanitor);
  }

  addReviewDecision(review: ReviewDecisionRecord): ReviewDecisionRecord {
    this.insertReview(review);
    return review;
  }

  insertReview(review: ReviewDecisionRecord): void {
    this.exec(
      `INSERT INTO reviews (id, task_id, decision, reviewer, summary, created_at) VALUES (${q(review.id)}, ${q(review.taskId)}, ${q(review.decision)}, ${q(review.reviewer)}, ${q(review.summary)}, ${q(review.createdAt)});`
    );
  }

  listReviews(taskId?: string): ReviewDecisionRecord[] {
    return this.query(
      taskId ? `SELECT * FROM reviews WHERE task_id = ${q(taskId)} ORDER BY created_at ASC` : `SELECT * FROM reviews ORDER BY created_at ASC`
    ).map(asReview);
  }

  upsertLock(lock: OwnershipLockRecord): OwnershipLockRecord {
    this.exec(`DELETE FROM ownership_locks WHERE id = ${q(lock.id)};
      INSERT INTO ownership_locks (id, task_id, path_glob, mode, status, created_at, updated_at)
      VALUES (${q(lock.id)}, ${q(lock.taskId)}, ${q(lock.pathGlob)}, ${q(lock.mode)}, ${q(lock.status)}, ${q(lock.createdAt)}, ${q(lock.updatedAt)});`);
    return lock;
  }

  replaceAllLocks(locks: OwnershipLockRecord[]): void {
    this.exec(`DELETE FROM ownership_locks;`);
    for (const lock of locks) {
      this.upsertLock(lock);
    }
  }

  listLocks(taskId?: string): OwnershipLockRecord[] {
    return this.query(
      taskId
        ? `SELECT * FROM ownership_locks WHERE task_id = ${q(taskId)} ORDER BY created_at ASC`
        : `SELECT * FROM ownership_locks ORDER BY created_at ASC`
    ).map(asLock);
  }

  upsertWorktree(worktree: WorktreeRecord): WorktreeRecord {
    this.exec(`DELETE FROM worktrees WHERE id = ${q(worktree.id)};
      INSERT INTO worktrees (id, task_id, branch_name, path, base_ref, status, created_at, updated_at)
      VALUES (${q(worktree.id)}, ${q(worktree.taskId)}, ${q(worktree.branchName)}, ${q(worktree.path)}, ${q(worktree.baseRef)}, ${q(worktree.status)}, ${q(worktree.createdAt)}, ${q(worktree.updatedAt)});`);
    return worktree;
  }

  listWorktrees(taskId?: string): WorktreeRecord[] {
    return this.query(
      taskId ? `SELECT * FROM worktrees WHERE task_id = ${q(taskId)} ORDER BY created_at DESC` : `SELECT * FROM worktrees ORDER BY created_at DESC`
    ).map(asWorktree);
  }

  upsertCapabilities(snapshots: ProviderCapabilitySnapshot[]): void {
    this.exec(`DELETE FROM capabilities;`);
    for (const snapshot of snapshots) {
      this.exec(
        `INSERT INTO capabilities (runtime, provider, snapshot, updated_at) VALUES (${q(snapshot.runtime)}, ${q(snapshot.provider)}, ${q(toJson(snapshot))}, ${q(snapshot.detectedAt)});`
      );
    }
  }

  replaceCapabilities(snapshots: ProviderCapabilitySnapshot[]): void {
    this.upsertCapabilities(snapshots);
  }

  listCapabilities(): ProviderCapabilitySnapshot[] {
    return this.query(`SELECT snapshot FROM capabilities ORDER BY runtime ASC`).map((row) =>
      safeParseJson(String(row.snapshot), {
        runtime: "generic",
        provider: "generic",
        title: "Unknown",
        command: null,
        version: null,
        installStatus: "unknown",
        authStatus: "unknown",
        detectedAt: nowIso(),
        models: [],
        supportsNativeSubagents: false,
        supportsCloud: false,
        supportsContextStats: false,
        supportsCompaction: false,
        supportsModelSelection: false,
        supportsModeSelection: false,
        supportsBestOfN: false,
        supportsInternetControl: false,
        supportsReadOnlyPlanMode: false,
        supportsWorktreeExecution: false,
        exactUsageSupported: false,
        nativeStatsSupported: false,
        maxContextWindow: 0,
        maxOutputTokens: 0,
        costTier: "unknown",
        quotaState: "unknown",
        telemetryConfidence: 0,
        notes: []
      } satisfies ProviderCapabilitySnapshot)
    );
  }

  getCollections(goalId: string): StoreCollections {
    const board = this.getBoardState(goalId);
    return {
      tasks: board.tasks,
      sessions: board.sessions,
      runs: board.runs,
      events: board.events,
      logs: board.logs,
      janitorResults: board.janitorResults,
      reviews: board.reviews,
      locks: board.locks,
      worktrees: board.worktrees,
      capabilities: board.capabilities,
      conversation: board.conversation
    };
  }

  getBoardState(goalId: string): BoardState {
    const boardWithoutStats = {
      goalId,
      conversation: this.getConversation(goalId),
      tasks: this.listTasks(goalId),
      sessions: this.listSessions(),
      runs: this.listRuns(),
      logs: this.listLogs(),
      events: this.listEvents(),
      janitorResults: this.listJanitorResults(),
      reviews: this.listReviews(),
      locks: this.listLocks(),
      worktrees: this.listWorktrees(),
      capabilities: this.listCapabilities(),
      projectSnapshot: null
    };
    return {
      ...boardWithoutStats,
      stats: computeStats(boardWithoutStats)
    };
  }

  getTaskDetail(taskId: string): TaskDetailPayload | null {
    const task = this.getTask(taskId);
    if (!task) {
      return null;
    }
    const tasks = this.listTasks(task.goalId);
    return {
      task,
      children: tasks.filter((candidate) => candidate.parentId === taskId),
      dependencies: tasks.filter((candidate) => task.dependencies.includes(candidate.id)),
      session: this.getSessionByTask(taskId),
      runs: this.listRuns(taskId),
      events: this.listEvents().filter((event) => event.entityId === taskId),
      logs: this.listLogs(taskId),
      janitorResults: this.listJanitorResults(taskId),
      reviews: this.listReviews(taskId),
      locks: this.listLocks(taskId),
      worktree: this.listWorktrees(taskId)[0] ?? null,
      diffText: ""
    };
  }
}
