export type TaskStatus =
  | "backlog"
  | "ready"
  | "running"
  | "review"
  | "blocked"
  | "done"
  | "failed"
  | "rejected";

export type TaskType =
  | "planning"
  | "explore"
  | "implement"
  | "refactor"
  | "test-fix"
  | "review"
  | "docs"
  | "verify"
  | "merge";

export type AgentMode =
  | "read_only_strategist"
  | "single"
  | "native_subagents"
  | "orchestrator_subtasks"
  | "hybrid";

export type DelegationMode =
  | "single"
  | "native_subagents"
  | "orchestrator_subtasks"
  | "hybrid";

export type Locality = "local" | "cloud";
export type SessionStatus = "idle" | "running" | "waiting" | "complete" | "failed" | "cancelled";
export type QuotaState = "healthy" | "caution" | "degraded" | "exhausted" | "unknown";
export type TokenAccountingTier = "exact" | "native" | "estimated";
export type HeadroomBand =
  | "healthy"
  | "caution"
  | "compact_or_fork"
  | "migrate"
  | "hard_stop";

export type RuntimeId =
  | "codex-local"
  | "codex-cloud"
  | "claude"
  | "gemini"
  | "cursor"
  | "opencode"
  | "generic";

export type ProviderId =
  | "openai"
  | "anthropic"
  | "google"
  | "cursor"
  | "opencode"
  | "generic";

export type VerificationCheckType =
  | "test"
  | "lint"
  | "typecheck"
  | "build"
  | "path_exists"
  | "file_contains"
  | "diff_sanity"
  | "owned_file_boundary"
  | "merge_conflict"
  | "untracked_files"
  | "review";

export interface JsonRecord {
  [key: string]: JsonValue;
}

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonRecord
  | JsonValue[];

export interface TaskTokenBudget {
  predictedPromptTokens: number;
  predictedOutputTokens: number;
  predictedGrowthTokens: number;
  sessionOccupancyEstimate: number;
  subagentOverheadTokens: number;
  headroomRatio: number;
  headroomBand: HeadroomBand;
  tier: TokenAccountingTier;
  confidence: number;
}

export interface RouteScoreBreakdown {
  taskFit: number;
  capabilityMatch: number;
  historicalSuccess: number;
  latencyFit: number;
  costFit: number;
  contextFit: number;
  contentionPenalty: number;
  policyPenalty: number;
  total: number;
}

export interface RouteDecisionRationale {
  summary: string;
  hardGuards: string[];
  scoring: RouteScoreBreakdown;
  alternatives: Array<{
    runtime: RuntimeId;
    provider: ProviderId;
    total: number;
    reason: string;
  }>;
}

export interface ExecutionPlan {
  runtime: RuntimeId;
  provider: ProviderId;
  model: string;
  locality: Locality;
  agentMode: AgentMode;
  delegationMode: DelegationMode;
  sessionStrategy:
    | "continue_in_session"
    | "fork_fresh_session"
    | "compact_then_continue"
    | "spawn_child"
    | "migrate_provider";
  verificationStrategy: "deterministic" | "deterministic_plus_agent_review";
  internetAccess: "inherit" | "required" | "forbidden";
  maxIterations: number;
  useWorktree: boolean;
  rationale: RouteDecisionRationale;
  tokenBudget: TaskTokenBudget;
}

export interface ProviderCapabilitySnapshot {
  runtime: RuntimeId;
  provider: ProviderId;
  title: string;
  command: string | null;
  version: string | null;
  installStatus: "installed" | "missing" | "unknown";
  authStatus: "authenticated" | "logged_out" | "unknown" | "unsupported";
  detectedAt: string;
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
  costTier: "low" | "medium" | "high" | "unknown";
  quotaState: QuotaState;
  telemetryConfidence: number;
  notes: string[];
}

export interface TaskRecord {
  id: string;
  goalId: string;
  parentId: string | null;
  title: string;
  description: string;
  status: TaskStatus;
  role: "strategist" | "worker" | "reviewer" | "janitor" | "manager";
  taskType: TaskType;
  agentMode: AgentMode;
  delegationPolicy: DelegationMode;
  locality: Locality;
  runtimeCandidates: RuntimeId[];
  providerCandidates: ProviderId[];
  preferredRuntime: RuntimeId | null;
  preferredProvider: ProviderId | null;
  chosenRuntime: RuntimeId | null;
  chosenProvider: ProviderId | null;
  chosenModel: string | null;
  ownedFiles: string[];
  readOnlyPaths: string[];
  verificationPolicy: VerificationCheckType[];
  tokenBudget: TaskTokenBudget;
  dependencies: string[];
  attempts: number;
  maxAttempts: number;
  routingRationale: RouteDecisionRationale | null;
  constraints: JsonRecord;
  createdAt: string;
  updatedAt: string;
}

export interface TaskDependencyRecord {
  id: string;
  taskId: string;
  dependsOnTaskId: string;
}

export interface SessionRecord {
  id: string;
  taskId: string;
  runtime: RuntimeId;
  provider: ProviderId;
  model: string;
  mode: AgentMode;
  localOrCloud: Locality;
  nativeStatsSupported: boolean;
  exactUsageSupported: boolean;
  compactionSupported: boolean;
  contextWindow: number;
  maxOutputTokens: number;
  estimatedContextUsed: number;
  nativeContextUsed: number | null;
  headroom: number;
  quotaState: QuotaState;
  status: SessionStatus;
  externalSessionId: string | null;
  startedAt: string;
  updatedAt: string;
}

export interface RunRecord {
  id: string;
  taskId: string;
  sessionId: string | null;
  attempt: number;
  status: "queued" | "running" | "complete" | "failed" | "cancelled";
  startedAt: string;
  endedAt: string | null;
  exitCode: number | null;
  summary: string;
}

export interface EventRecord {
  id: string;
  entityType: "task" | "session" | "run" | "adapter" | "review" | "janitor" | "system";
  entityId: string;
  eventType: string;
  payload: JsonValue;
  createdAt: string;
}

export interface LogRecord {
  id: string;
  runId: string;
  stream: "stdout" | "stderr" | "system";
  message: string;
  createdAt: string;
}

export interface JanitorCheckDefinition {
  type: VerificationCheckType;
  label: string;
  command?: string;
  path?: string;
  contains?: string;
}

export interface JanitorResultRecord {
  id: string;
  taskId: string;
  runId: string | null;
  status: "pending" | "passed" | "failed";
  checks: Array<JanitorCheckDefinition & { status: "pending" | "passed" | "failed"; output: string }>;
  diffSummary: string;
  createdAt: string;
}

export interface ReviewDecisionRecord {
  id: string;
  taskId: string;
  decision: "approve" | "reject" | "retry" | "reopen";
  reviewer: string;
  summary: string;
  createdAt: string;
}

export interface OwnershipLockRecord {
  id: string;
  taskId: string;
  pathGlob: string;
  mode: "read" | "write";
  status: "active" | "released";
  createdAt: string;
  updatedAt: string;
}

export interface WorktreeRecord {
  id: string;
  taskId: string;
  branchName: string;
  path: string;
  baseRef: string;
  status: "active" | "preserved" | "cleaned";
  createdAt: string;
  updatedAt: string;
}

export interface StrategistMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
}

export interface StrategistConversation {
  messages: StrategistMessage[];
  latestPlanTaskId: string | null;
}

export interface ProjectRootSummary {
  path: string;
  kind: "node" | "python" | "docs" | "workspace";
  name: string;
  summary: string;
  keyFiles: string[];
}

export interface ProjectEvidenceMatch {
  term: string;
  path: string;
}

export interface OperationalHealthSnapshot {
  totalTasks: number;
  runningTasks: number;
  failedTasks: number;
  blockedTasks: number;
  reviewTasks: number;
  liveSessions: number;
  authenticatedRuntimes: string[];
  degradedRuntimes: string[];
  latestFailures: Array<{
    taskId: string;
    title: string;
    runtime: string | null;
    updatedAt: string;
  }>;
}

export interface ProjectSnapshot {
  generatedAt: string;
  repoRoot: string;
  projects: ProjectRootSummary[];
  dirtyFiles: string[];
  evidenceMatches: ProjectEvidenceMatch[];
  queryTerms: string[];
  operationalHealth: OperationalHealthSnapshot;
  activeRoot?: {
    path: string;
    name: string;
    kind: ProjectRootSummary["kind"];
    confidence: number;
    reason: string;
  };
  verificationFreshness?: {
    freshnessBand: "fresh" | "warm" | "stale" | "unknown";
    lastPassedAt: string | null;
    lastFailedAt: string | null;
    summary: string;
  };
  runtimeHealth?: Array<{
    runtime: RuntimeId;
    provider: ProviderId;
    installStatus: "installed" | "missing" | "unknown";
    authStatus: "authenticated" | "logged_out" | "unknown" | "unsupported";
    detectedAt: string;
    status: "ready" | "needs_auth" | "missing" | "unsupported" | "degraded";
    ageMinutes: number;
    notes: string[];
  }>;
  evidenceBundle?: {
    matchedRoots: Array<{
      path: string;
      name: string;
      kind: ProjectRootSummary["kind"];
      confidence: number;
      reason: string;
    }>;
    matchedFiles: Array<{
      path: string;
      score: number;
      reason: string;
    }>;
    signals: string[];
  };
  workspaceLexicon?: string[];
}

export interface BoardState {
  goalId: string;
  conversation: StrategistConversation;
  tasks: TaskRecord[];
  sessions: SessionRecord[];
  runs: RunRecord[];
  logs: LogRecord[];
  events: EventRecord[];
  janitorResults: JanitorResultRecord[];
  reviews: ReviewDecisionRecord[];
  locks: OwnershipLockRecord[];
  worktrees: WorktreeRecord[];
  capabilities: ProviderCapabilitySnapshot[];
  projectSnapshot: ProjectSnapshot | null;
  stats: DashboardStats;
}

export interface TaskDetailPayload {
  task: TaskRecord;
  children: TaskRecord[];
  dependencies: TaskRecord[];
  session: SessionRecord | null;
  runs: RunRecord[];
  events: EventRecord[];
  logs: LogRecord[];
  janitorResults: JanitorResultRecord[];
  reviews: ReviewDecisionRecord[];
  locks: OwnershipLockRecord[];
  worktree: WorktreeRecord | null;
  diffText: string;
}

export interface CreateTaskInput {
  goalId: string;
  parentId?: string | null;
  title: string;
  description: string;
  role: TaskRecord["role"];
  taskType: TaskType;
  status?: TaskStatus;
  agentMode?: AgentMode;
  delegationPolicy?: DelegationMode;
  locality?: Locality;
  runtimeCandidates?: RuntimeId[];
  providerCandidates?: ProviderId[];
  preferredRuntime?: RuntimeId | null;
  preferredProvider?: ProviderId | null;
  ownedFiles?: string[];
  readOnlyPaths?: string[];
  verificationPolicy?: VerificationCheckType[];
  dependencies?: string[];
  tokenBudget?: Partial<TaskTokenBudget>;
  constraints?: JsonRecord;
}

export interface CreateTaskGraphInput {
  goalId: string;
  parentId: string | null;
  title: string;
  description: string;
  tasks: Array<CreateTaskInput & { localKey: string; dependsOnLocalKeys?: string[] }>;
}

export interface StrategistRequest {
  goalId: string;
  message: string;
}

export interface StrategistResponse {
  reply: string;
  createdTaskIds: string[];
  rootTaskId: string | null;
}

export interface QueueMetrics {
  readyTasks: number;
  runningTasks: number;
  reviewTasks: number;
  blockedTasks: number;
  mergeQueueDepth: number;
}

export interface DashboardStats {
  queue: QueueMetrics;
  tokenBands: Record<HeadroomBand, number>;
  runtimeLoad: Record<RuntimeId, number>;
}

export const DEFAULT_TOKEN_BUDGET: TaskTokenBudget = {
  predictedPromptTokens: 1400,
  predictedOutputTokens: 900,
  predictedGrowthTokens: 500,
  sessionOccupancyEstimate: 4000,
  subagentOverheadTokens: 700,
  headroomRatio: 0.62,
  headroomBand: "healthy",
  tier: "estimated",
  confidence: 0.45
};
