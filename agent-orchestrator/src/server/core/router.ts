import {
  ExecutionPlan,
  ProviderCapabilitySnapshot,
  ProviderId,
  RuntimeId,
  SessionRecord,
  TaskRecord
} from "../../shared/types";
import { TokenBudgetManager } from "./token-budget";

const TASK_RUNTIME_FIT: Record<TaskRecord["taskType"], Partial<Record<RuntimeId, number>>> = {
  planning: { "codex-local": 72, claude: 75, gemini: 84, opencode: 80, "codex-cloud": 62, cursor: 45, generic: 25 },
  explore: { gemini: 88, claude: 82, opencode: 76, "codex-local": 68, "codex-cloud": 64, cursor: 40, generic: 25 },
  implement: { "codex-local": 90, opencode: 82, claude: 74, "codex-cloud": 78, gemini: 55, cursor: 60, generic: 30 },
  refactor: { "codex-local": 88, opencode: 78, claude: 74, "codex-cloud": 76, gemini: 60, cursor: 58, generic: 28 },
  "test-fix": { "codex-local": 87, opencode: 80, claude: 70, "codex-cloud": 72, gemini: 50, cursor: 55, generic: 30 },
  review: { claude: 84, "codex-local": 76, opencode: 72, gemini: 68, "codex-cloud": 65, cursor: 48, generic: 24 },
  docs: { claude: 78, gemini: 72, "codex-local": 64, opencode: 70, "codex-cloud": 58, cursor: 44, generic: 26 },
  verify: { "codex-local": 85, claude: 70, opencode: 68, "codex-cloud": 66, gemini: 54, cursor: 40, generic: 22 },
  merge: { "codex-local": 82, claude: 52, opencode: 50, "codex-cloud": 46, gemini: 30, cursor: 28, generic: 20 }
};

export class TaskRouter {
  constructor(private readonly tokenManager: TokenBudgetManager) {}

  routeTask(
    task: TaskRecord,
    capabilities: ProviderCapabilitySnapshot[],
    session?: SessionRecord | null
  ): ExecutionPlan {
    const scoped = capabilities
      .filter((capability) => task.runtimeCandidates.includes(capability.runtime))
      .filter((capability) => task.providerCandidates.includes(capability.provider))
      .filter((capability) => capability.installStatus !== "missing" || capability.runtime === "generic");
    const installed = scoped.filter((capability) => capability.installStatus === "installed" || capability.runtime === "generic");
    const authenticated = installed.filter((capability) => capability.authStatus !== "logged_out");
    const candidatePool =
      authenticated.length > 0
        ? authenticated
        : installed.length > 0
          ? installed
          : scoped.length > 0
            ? scoped
            : capabilities;
    const candidates = candidatePool.map((capability) => this.scoreCandidate(task, capability, session));

    const viable = candidates.length > 0 ? candidates : capabilities.map((capability) => this.scoreCandidate(task, capability, session));
    const ranked = viable.sort((left, right) => right.score.total - left.score.total);
    const winner = ranked[0];
    if (!winner) {
      throw new Error(`No routing candidates available for task ${task.id}`);
    }

    const plan: ExecutionPlan = {
      runtime: winner.capability.runtime,
      provider: winner.capability.provider,
      model: this.pickModel(task, winner.capability),
      locality: winner.capability.supportsCloud && task.locality === "cloud" ? "cloud" : winner.capability.runtime === "codex-cloud" ? "cloud" : "local",
      agentMode: task.role === "strategist"
        ? "read_only_strategist"
        : task.delegationPolicy === "hybrid"
          ? "hybrid"
          : winner.capability.supportsNativeSubagents && /explore|planning/.test(task.taskType)
            ? "native_subagents"
            : "single",
      delegationMode: winner.capability.supportsNativeSubagents && task.delegationPolicy !== "single"
        ? task.delegationPolicy
        : task.taskType === "implement" || task.taskType === "refactor"
          ? "orchestrator_subtasks"
          : "single",
      sessionStrategy: this.tokenManager.chooseSessionStrategy(winner.budget, winner.capability),
      verificationStrategy: task.taskType === "review" || task.taskType === "verify"
        ? "deterministic_plus_agent_review"
        : "deterministic",
      internetAccess: Boolean(task.constraints.internetRequired)
        ? "required"
        : Boolean(task.constraints.internetForbidden)
          ? "forbidden"
          : "inherit",
      maxIterations: task.taskType === "planning" || task.taskType === "explore" ? 3 : 2,
      useWorktree: task.role !== "strategist" && !["planning", "explore", "review"].includes(task.taskType),
      rationale: {
        summary: `${winner.capability.title} selected for ${task.taskType} with ${Math.round(
          winner.budget.headroomRatio * 100
        )}% projected headroom and ${winner.capability.installStatus} runtime health.`,
        hardGuards: winner.hardGuards,
        scoring: winner.score,
        alternatives: ranked.slice(1, 4).map((candidate) => ({
          runtime: candidate.capability.runtime,
          provider: candidate.capability.provider,
          total: candidate.score.total,
          reason: candidate.summary
        }))
      },
      tokenBudget: winner.budget
    };

    return plan;
  }

  private scoreCandidate(
    task: TaskRecord,
    capability: ProviderCapabilitySnapshot,
    session?: SessionRecord | null
  ) {
    const budget = this.tokenManager.estimateBudget(task, capability, session);
    const hardGuards: string[] = [];
    let policyPenalty = 0;

    if (task.role === "strategist" && !capability.supportsReadOnlyPlanMode) {
      policyPenalty += 35;
      hardGuards.push("Strategist tasks require read-only or plan-mode capable runtimes.");
    }

    if (task.locality === "cloud" && !capability.supportsCloud) {
      policyPenalty += 20;
      hardGuards.push("Task requested cloud locality but runtime is local only.");
    }

    if ((task.taskType === "implement" || task.taskType === "refactor") && !capability.supportsWorktreeExecution && capability.runtime !== "codex-cloud") {
      policyPenalty += 15;
      hardGuards.push("Write-heavy tasks prefer runtimes that can operate in isolated worktrees.");
    }

    if (budget.headroomBand === "hard_stop") {
      policyPenalty += 50;
      hardGuards.push("Projected token headroom would hit the hard stop band.");
    }

    if (capability.authStatus === "logged_out") {
      policyPenalty += 25;
      hardGuards.push("Runtime is installed but not authenticated.");
    }

    const taskFit = TASK_RUNTIME_FIT[task.taskType][capability.runtime] ?? 20;
    const capabilityMatch =
      (capability.supportsNativeSubagents ? 8 : 0) +
      (capability.supportsContextStats ? 6 : 0) +
      (capability.supportsCompaction ? 5 : 0) +
      (capability.supportsWorktreeExecution && task.role !== "strategist" ? 7 : 0);
    const historicalSuccess = capability.installStatus === "installed" ? 12 : 2;
    const latencyFit = capability.runtime === "codex-cloud" ? 8 : 12;
    const costFit =
      capability.costTier === "low" ? 14 : capability.costTier === "medium" ? 10 : 5;
    const contextFit = Math.round(budget.headroomRatio * 28);
    const contentionPenalty = task.locality === "cloud" && capability.runtime !== "codex-cloud" ? 8 : 0;

    const total =
      taskFit +
      capabilityMatch +
      historicalSuccess +
      latencyFit +
      costFit +
      contextFit -
      contentionPenalty -
      policyPenalty;

    return {
      capability,
      budget,
      hardGuards,
      summary: `${capability.title}: taskFit=${taskFit}, contextFit=${contextFit}, policyPenalty=${policyPenalty}`,
      score: {
        taskFit,
        capabilityMatch,
        historicalSuccess,
        latencyFit,
        costFit,
        contextFit,
        contentionPenalty,
        policyPenalty,
        total
      }
    };
  }

  private pickModel(task: TaskRecord, capability: ProviderCapabilitySnapshot): string {
    const preferred = task.constraints.preferredModel;
    if (typeof preferred === "string" && capability.models.includes(preferred)) {
      return preferred;
    }
    if (capability.runtime === "opencode") {
      return capability.models[0] ?? "openai/gpt-5.4";
    }
    if (task.taskType === "planning" || task.taskType === "explore") {
      return capability.models[0] ?? "default";
    }
    return capability.models[1] ?? capability.models[0] ?? "default";
  }
}
