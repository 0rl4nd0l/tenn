import {
  DEFAULT_TOKEN_BUDGET,
  HeadroomBand,
  ProviderCapabilitySnapshot,
  SessionRecord,
  TaskRecord,
  TaskTokenBudget
} from "../../shared/types";

export const TOKEN_POLICY = {
  healthy: 0.55,
  caution: 0.35,
  compactOrFork: 0.2,
  hardStop: 0.1
} as const;

export class TokenBudgetManager {
  getBand(headroomRatio: number): HeadroomBand {
    if (headroomRatio < TOKEN_POLICY.hardStop) {
      return "hard_stop";
    }
    if (headroomRatio < TOKEN_POLICY.compactOrFork) {
      return "migrate";
    }
    if (headroomRatio < TOKEN_POLICY.caution) {
      return "compact_or_fork";
    }
    if (headroomRatio < TOKEN_POLICY.healthy) {
      return "caution";
    }
    return "healthy";
  }

  estimateBudget(
    task: TaskRecord,
    capability: ProviderCapabilitySnapshot,
    session?: SessionRecord | null
  ): TaskTokenBudget {
    const descriptionWeight = Math.max(1, Math.ceil(task.description.length / 180));
    const fileWeight = Math.max(1, task.ownedFiles.length + task.readOnlyPaths.length * 0.5);
    const taskTypeWeight =
      task.taskType === "planning" || task.taskType === "review"
        ? 0.8
        : task.taskType === "explore"
          ? 1.4
          : task.taskType === "implement" || task.taskType === "refactor"
            ? 1.2
            : 1;
    const ambiguityWeight = /\?|\bexplore\b|\binvestigate\b|\bunknown\b/i.test(task.description) ? 1.35 : 1;
    const basePrompt = 900 + descriptionWeight * 260 + fileWeight * 180;
    const predictedPromptTokens = Math.round(basePrompt * taskTypeWeight);
    const predictedOutputTokens = Math.round((550 + descriptionWeight * 150) * ambiguityWeight);
    const predictedGrowthTokens = Math.round(predictedPromptTokens * 0.4 + predictedOutputTokens * 0.3);
    const sessionOccupancyEstimate = session?.estimatedContextUsed ?? task.tokenBudget.sessionOccupancyEstimate ?? DEFAULT_TOKEN_BUDGET.sessionOccupancyEstimate;
    const effectiveWindow = Math.max(8_000, capability.maxContextWindow - capability.maxOutputTokens);
    const nextTurn = predictedPromptTokens + predictedOutputTokens + predictedGrowthTokens;
    const projectedUsed = sessionOccupancyEstimate + nextTurn;
    const headroomRatio = Math.max(0, (effectiveWindow - projectedUsed) / effectiveWindow);
    const tier =
      session?.exactUsageSupported
        ? "exact"
        : session?.nativeStatsSupported || capability.nativeStatsSupported
          ? "native"
          : "estimated";
    const confidence =
      tier === "exact"
        ? 0.95
        : tier === "native"
          ? capability.telemetryConfidence * 0.9
          : capability.telemetryConfidence * 0.75;

    return {
      predictedPromptTokens,
      predictedOutputTokens,
      predictedGrowthTokens,
      sessionOccupancyEstimate,
      subagentOverheadTokens: task.delegationPolicy === "single" ? 250 : 700,
      headroomRatio,
      headroomBand: this.getBand(headroomRatio),
      tier,
      confidence: Math.max(0.1, Math.min(0.99, confidence))
    };
  }

  chooseSessionStrategy(
    budget: TaskTokenBudget,
    capability: ProviderCapabilitySnapshot
  ): "continue_in_session" | "fork_fresh_session" | "compact_then_continue" | "spawn_child" | "migrate_provider" {
    if (budget.headroomBand === "hard_stop") {
      return "migrate_provider";
    }
    if (budget.headroomBand === "migrate") {
      return "migrate_provider";
    }
    if (budget.headroomBand === "compact_or_fork") {
      return "fork_fresh_session";
    }
    if (budget.headroomBand === "caution") {
      return budget.predictedOutputTokens >= 900 ? "spawn_child" : "fork_fresh_session";
    }
    return "fork_fresh_session";
  }
}
