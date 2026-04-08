import type {
  CreateTaskInput,
  ProjectSnapshot,
  RuntimeId,
  StrategistConversation,
  TaskRecord,
  TaskType
} from "../../shared/types";
import { DEFAULT_TOKEN_BUDGET } from "../../shared/types";
import { createId } from "../utils/id";
import { nowIso } from "../utils/time";

export interface StrategistPlan {
  mode: "delegate" | "respond";
  reply: string;
  rootTask: CreateTaskInput | null;
  childTasks: StrategistChildTaskInput[];
}

export interface StrategistContext {
  conversation?: StrategistConversation;
  projectSnapshot?: ProjectSnapshot | null;
}

type StrategistWorkspaceSnapshot = ProjectSnapshot & {
  activeRoot?: {
    path: string;
    name: string;
    kind: ProjectSnapshot["projects"][number]["kind"];
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
    provider: string;
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
      kind: ProjectSnapshot["projects"][number]["kind"];
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
};

/**
 * Strategist decision engine.
 *
 * Responsibilities:
 * - Classify incoming user intent.
 * - Decide whether to answer directly or emit a delegated task graph.
 * - Keep strategist itself read-only and route execution to child tasks.
 *
 * High-level flow:
 * 1) Assessment questions -> respond with snapshot assessment (no task creation).
 * 2) Ambiguous workspace target with weak evidence -> clarification response.
 * 3) Non-delegable conversational prompts -> concise direct response.
 * 4) Delegable engineering requests -> root planning task + ordered child slices.
 */
export class StrategistService {
  plan(goalId: string, message: string, context?: StrategistContext): StrategistPlan {
    const profile = buildRequestProfile(message);
    const conversation = context?.conversation;
    const projectSnapshot = context?.projectSnapshot ?? null;

    if (isAssessmentQuery(message)) {
      return {
        mode: "respond",
        reply: buildAssessmentReply(projectSnapshot),
        rootTask: null,
        childTasks: []
      };
    }

    if (shouldClarifyAgainstWorkspace(profile, projectSnapshot)) {
      return {
        mode: "respond",
        reply: buildWorkspaceClarificationReply(message, projectSnapshot),
        rootTask: null,
        childTasks: []
      };
    }

    if (!shouldDelegate(profile)) {
      return {
        mode: "respond",
        reply: buildConversationalReply(message, conversation, projectSnapshot),
        rootTask: null,
        childTasks: []
      };
    }

    const topic = summarizeTopic(message);
    const rootTask = makeTask(goalId, {
      title: `Strategic plan: ${topic}`,
      description: message,
      role: "strategist",
      taskType: "planning",
      status: "done",
      agentMode: "read_only_strategist",
      delegationPolicy: "orchestrator_subtasks",
      runtimeCandidates: ["claude", "gemini", "opencode", "codex-local"],
      readOnlyPaths: ["./"],
      verificationPolicy: ["diff_sanity"],
      constraints: {
        intent: profile.intent,
        strategyOnly: true,
        domain: profile.domain,
        themeDirection: profile.queerVisualDirection ? "queer_expressive" : null,
        evidenceMatches: projectSnapshot?.evidenceMatches.slice(0, 6).map((match) => match.path) ?? []
      }
    });

    const slices = buildTaskSlices(message, profile, projectSnapshot);
    const childTasks = slices.map((slice) => ({
      localKey: slice.localKey,
      dependsOnLocalKeys: slice.dependsOnLocalKeys,
      ...makeTask(goalId, {
        title: slice.title,
        description: slice.description,
        role: slice.role,
        taskType: slice.taskType,
        status: slice.dependsOnLocalKeys.length === 0 ? "ready" : "backlog",
        agentMode: slice.role === "strategist" ? "read_only_strategist" : "single",
        delegationPolicy: slice.delegationPolicy,
        runtimeCandidates: slice.runtimeCandidates,
        providerCandidates: slice.providerCandidates,
        ownedFiles: slice.ownedFiles,
        readOnlyPaths: slice.readOnlyPaths,
        verificationPolicy: slice.verificationPolicy,
        constraints: slice.constraints
      })
    }));

    return {
      mode: "delegate",
      reply: buildDelegationReply(profile, childTasks.length, projectSnapshot),
      rootTask,
      childTasks
    };
  }
}

function buildTaskSlices(
  message: string,
  profile: RequestProfile,
  projectSnapshot: ProjectSnapshot | null
): SliceTemplate[] {
  if (profile.localInspectionRequest) {
    return [
      {
        localKey: "inspection",
        title: "Local inspection answer",
        description:
          "Inspect local files and runtime state relevant to the user's question, then return a direct answer with concrete findings and short evidence references. Do not propose unrelated plans.",
        role: "worker",
        taskType: "explore",
        delegationPolicy: "single",
        runtimeCandidates: ["opencode", "codex-local", "claude", "gemini"],
        providerCandidates: ["opencode", "openai", "anthropic", "google"],
        ownedFiles: [],
        readOnlyPaths: ["./"],
        verificationPolicy: ["diff_sanity"],
        constraints: {
          readOnly: true,
          directAnswerRequired: true,
          userQuestion: message
        },
        dependsOnLocalKeys: []
      }
    ];
  }

  // Discovery is always first and read-only. It establishes repo context,
  // constraints, and risk before implementation/review lanes.
  const slices: SliceTemplate[] = [
    {
      localKey: "discovery",
      title: profile.domain === "ingestion" ? "PDF ingestion discovery and failure map" : "Repo discovery and execution plan",
      description:
        profile.domain === "ingestion"
          ? "Inspect the current PDF ingestion stack, isolate the parsing and extraction stages, capture the dominant error modes, and define measurable accuracy gates without making edits."
          : "Read the repository, identify the impacted surfaces, validate constraints, and refine the delegated execution plan without making edits.",
      role: "worker",
      taskType: "explore",
      delegationPolicy: "orchestrator_subtasks",
      runtimeCandidates: ["gemini", "claude", "opencode", "codex-local"],
      providerCandidates: ["google", "anthropic", "opencode", "openai"],
      ownedFiles: [],
      readOnlyPaths: ["./"],
      verificationPolicy: ["diff_sanity"],
      constraints: {
        readOnly: true,
        maximizeContext: true,
        domain: profile.domain
      },
      dependsOnLocalKeys: []
    }
  ];

  const implementationKeys: string[] = [];
  const evidenceOwnedFiles = deriveOwnedFiles(projectSnapshot, profile.domain);
  const evidenceReadPaths = deriveReadOnlyPaths(projectSnapshot, profile.domain);

  if (profile.wantsBackend && !profile.discoveryOnly) {
    slices.push({
      localKey: "backend",
      title:
        profile.domain === "ingestion"
          ? "PDF ingestion accuracy hardening"
          : "Backend control-plane implementation",
      description:
        profile.domain === "ingestion"
          ? "Improve extraction accuracy in the PDF ingestion path: normalize parsing stages, add deterministic evaluation hooks, tighten failure classification, and make regressions measurable."
          : "Implement or update the orchestration backend: routing, scheduling, storage, execution wiring, janitor verification, and merge/review flow.",
      role: "worker",
      taskType: "implement",
      delegationPolicy: "hybrid",
      runtimeCandidates: ["codex-local", "opencode", "claude", "codex-cloud"],
      providerCandidates: ["openai", "opencode", "anthropic"],
      ownedFiles:
        profile.domain === "ingestion"
          ? evidenceOwnedFiles.length > 0
            ? evidenceOwnedFiles
            : ["financial-engine_v2/scripts/**", "financial-engine_v2/backend/**", "docs/marketindex_architecture_snapshot.md"]
          : ["agent-orchestrator/src/server/**", "agent-orchestrator/scripts/**", "agent-orchestrator/tests/**"],
      readOnlyPaths:
        profile.domain === "ingestion"
          ? evidenceReadPaths.length > 0
            ? evidenceReadPaths
            : ["financial-engine_v2/**", "docs/**", "reports/**"]
          : ["agent-orchestrator/src/web/**"],
      verificationPolicy:
        profile.domain === "ingestion"
          ? ["test", "diff_sanity", "owned_file_boundary"]
          : ["typecheck", "test", "diff_sanity", "owned_file_boundary"],
      constraints: {
        intent: profile.intent,
        domain: profile.domain
      },
      dependsOnLocalKeys: ["discovery"]
    });
    implementationKeys.push("backend");
  }

  if (profile.wantsFrontend && !profile.discoveryOnly) {
    slices.push({
      localKey: "frontend",
      title:
        profile.queerVisualDirection
          ? "Queer-forward visual system and operator UX"
          : "Frontend strategist and kanban UI",
      description:
        profile.queerVisualDirection
          ? "Rework the UI into a queer-forward, expressive operator surface with stronger color, typography, iconography, and motion while preserving legibility, task visibility, and review control."
          : "Build the React strategist/kanban interface, wire it to board and task detail state, and surface routing rationale, tokens, logs, and review actions.",
      role: "worker",
      taskType: "implement",
      delegationPolicy: "single",
      runtimeCandidates: ["codex-local", "cursor", "opencode", "claude"],
      providerCandidates: ["openai", "cursor", "opencode", "anthropic"],
      ownedFiles: ["agent-orchestrator/src/web/**", "agent-orchestrator/index.html", "agent-orchestrator/vite.config.ts"],
      readOnlyPaths: ["agent-orchestrator/src/server/**"],
      verificationPolicy: ["build", "diff_sanity", "owned_file_boundary"],
      constraints: {
        intent: profile.intent,
        visualQuality: profile.queerVisualDirection ? "queer_expressive" : "strong-v1"
      },
      dependsOnLocalKeys: ["discovery"]
    });
    implementationKeys.push("frontend");
  }

  if (profile.wantsDocs && !profile.discoveryOnly) {
    slices.push({
      localKey: "docs",
      title: "Documentation polish and usage guidance",
      description:
        "Write or update the README, ADRs, and operational notes so the orchestrator can be run and extended without guessing.",
      role: "worker",
      taskType: "docs",
      delegationPolicy: "single",
      runtimeCandidates: ["claude", "codex-local", "opencode"],
      providerCandidates: ["anthropic", "openai", "opencode"],
      ownedFiles: ["agent-orchestrator/README.md", "agent-orchestrator/docs/**"],
      readOnlyPaths: ["agent-orchestrator/src/**"],
      verificationPolicy: ["diff_sanity", "owned_file_boundary"],
      constraints: {
        docsRequired: true
      },
      dependsOnLocalKeys: implementationKeys.length > 0 ? [...implementationKeys] : ["discovery"]
    });
    implementationKeys.push("docs");
  }

  slices.push({
    localKey: "verify",
    title:
      profile.domain === "ingestion"
        ? "Ingestion verification and regression review"
        : "Deterministic verification and review",
    description:
      profile.domain === "ingestion"
        ? "Run deterministic checks, inspect PDF diffs and parser outputs, and challenge whether the accuracy gains are real, repeatable, and worth merging."
        : "Run the janitor gates, inspect diffs, challenge routing and token behavior, and produce approval or retry recommendations.",
    role: "reviewer",
    taskType: "verify",
    delegationPolicy: "orchestrator_subtasks",
    runtimeCandidates: ["claude", "codex-local", "gemini", "opencode"],
    providerCandidates: ["anthropic", "openai", "google", "opencode"],
    ownedFiles: [],
    readOnlyPaths: profile.domain === "ingestion" ? ["financial-engine_v2/**", "docs/**", "reports/**"] : ["./"],
    verificationPolicy: ["review", "test", "build", "diff_sanity"],
    constraints: {
      deterministicFirst: true,
      domain: profile.domain
    },
    dependsOnLocalKeys: implementationKeys.length > 0 ? implementationKeys : ["discovery"]
  });

  return slices;
}

function buildDelegationReply(
  profile: RequestProfile,
  childTaskCount: number,
  projectSnapshot: ProjectSnapshot | null
): string {
  if (profile.localInspectionRequest) {
    const activeRoot = toWorkspaceSnapshot(projectSnapshot)?.activeRoot?.name ?? "the workspace";
    return `I'll check that in ${activeRoot} and send you a direct answer as soon as it completes.`;
  }

  const domainLine =
    profile.domain === "ingestion"
      ? "I’m treating this as an accuracy program: failure taxonomy, deterministic evals, targeted implementation, and verification."
      : profile.queerVisualDirection
        ? "I’m treating this as an explicit visual-direction request, not a joke prompt: stronger identity, clearer affordances, and still operator-grade legibility."
        : "I will keep the strategist read-only and route the work through delegated tasks.";

  const scope =
    profile.discoveryOnly
      ? "a read-only discovery and verification lane"
      : profile.wantsBackend && profile.wantsFrontend
      ? "parallel backend and frontend lanes"
      : profile.wantsBackend
        ? "a backend-heavy execution lane"
        : profile.wantsFrontend
          ? "a frontend-heavy execution lane"
          : "targeted execution lanes";

  const evidenceLine =
    projectSnapshot && projectSnapshot.evidenceMatches.length > 0
      ? `Grounding this in repo evidence from ${projectSnapshot.evidenceMatches
          .slice(0, 3)
          .map((match) => match.path)
          .join(", ")}.`
      : null;

  return [domainLine, `Initial task graph: ${childTaskCount} child tasks with discovery first and ${scope}.`, evidenceLine, "Routing stays recursive, token-aware, and worktree-isolated for write scopes."]
    .filter((line): line is string => Boolean(line))
    .join(" ");
}

function buildAssessmentReply(projectSnapshot: ProjectSnapshot | null): string {
  const view = toWorkspaceSnapshot(projectSnapshot);
  if (!view) {
    return "I do not have a fresh workspace snapshot yet. Ask me again after the board loads or give me a concrete system area to inspect.";
  }

  const health = view.operationalHealth;
  const activeRoot = view.activeRoot ?? {
    path: ".",
    name: "workspace",
    kind: "workspace",
    confidence: 0.25,
    reason: "fallback workspace view"
  };
  const matchedRoots = view.evidenceBundle?.matchedRoots ?? summarizeRoots(view);
  const matchedFiles = view.evidenceBundle?.matchedFiles ?? summarizeFiles(view);
  const runtimeLine = summarizeRuntimeHealth(view);
  const verificationLine = view.verificationFreshness?.summary ?? "no fresh verification snapshot";
  const riskLine = summarizeRiskLine(view);
  const nextStep = chooseNextAssessmentStep(view);

  return [
    `Active root: ${activeRoot.name}${activeRoot.path !== "." ? ` [${activeRoot.path}]` : ""} (${Math.round(activeRoot.confidence * 100)}% confidence) because ${activeRoot.reason}.`,
    `Evidence: roots ${formatRoots(matchedRoots)}; files ${formatFiles(matchedFiles)}.`,
    `Current workspace state: ${health.runningTasks} running, ${health.reviewTasks} in review, ${health.failedTasks} failed, ${health.blockedTasks} blocked, ${health.liveSessions} live sessions; ${runtimeLine}.`,
    `Verification: ${verificationLine}.`,
    `Risk: ${riskLine}.`,
    view.workspaceLexicon?.length ? `Lexicon: ${view.workspaceLexicon.slice(0, 3).join("; ")}.` : null,
    `Next: ${nextStep}.`
  ]
    .filter((line): line is string => Boolean(line))
    .join(" ");
}

function buildWorkspaceClarificationReply(message: string, projectSnapshot: ProjectSnapshot | null): string {
  const view = toWorkspaceSnapshot(projectSnapshot);
  if (!view) {
    return "I do not have enough workspace evidence for that subsystem yet. Point me at the relevant project area or ask for a repo scan first.";
  }

  const topic = summarizeTopic(message);
  const roots = view.evidenceBundle?.matchedRoots ?? summarizeRoots(view);
  return [
    `I do not have strong repo evidence for "${topic}" in the current workspace.`,
    `Closest roots: ${formatRoots(roots) || "no clear project roots detected"}.`,
    `Active guess: ${view.activeRoot?.name ?? "workspace"}${view.activeRoot?.path && view.activeRoot.path !== "." ? ` [${view.activeRoot.path}]` : ""} (${Math.round((view.activeRoot?.confidence ?? 0.25) * 100)}%).`,
    "If you mean one of those existing areas, name it directly and I will route work there instead of inventing a subsystem."
  ].join(" ");
}

function buildConversationalReply(
  message: string,
  conversation?: StrategistConversation,
  projectSnapshot?: ProjectSnapshot | null
): string {
  const normalized = normalizeMessage(message);
  const priorTopic = extractLastActionableTopic(conversation);
  const view = toWorkspaceSnapshot(projectSnapshot);

  if (isGreeting(normalized)) {
    return "Hi. Talk to me normally. If something needs execution, I'll handle it.";
  }

  if (isAcknowledgement(normalized)) {
    return priorTopic
      ? `Understood. I can keep discussing ${priorTopic} here, or start working on it if you're ready.`
      : "Understood. Keep chatting, and I'll start execution only when needed.";
  }

  if (/what( do)? you think|what u think|thoughts|opinion/i.test(normalized)) {
    if (!priorTopic && view) {
      return `Directionally yes. The strongest signal is ${formatRoots(view.evidenceBundle?.matchedRoots ?? summarizeRoots(view))}, especially ${formatFiles(view.evidenceBundle?.matchedFiles ?? summarizeFiles(view))}. I’d start there and keep the next step small.`;
    }
    if (priorTopic) {
      if (/pdf|ingest|parser|extract/i.test(priorTopic)) {
        const evidenceLine =
          view?.evidenceBundle?.matchedFiles.length
            ? ` Strongest current file signals are ${formatFiles(view.evidenceBundle.matchedFiles)}.`
            : "";
        return `Directionally yes, but I’d narrow it into measurable accuracy work: define a golden PDF corpus, classify failure modes, instrument stage-by-stage quality, and gate changes with deterministic evals.${evidenceLine}`;
      }
      return `Directionally yes. I would tighten the scope around concrete outcomes, explicit failure modes, and a verification plan before dispatching more work on ${priorTopic}.`;
    }
    return view
      ? `Directionally yes. Based on ${formatRoots(view.evidenceBundle?.matchedRoots ?? summarizeRoots(view))} and ${formatFiles(view.evidenceBundle?.matchedFiles ?? summarizeFiles(view))}, I would keep the next step small, measurable, and verification-first.`
      : "I can give a view, but I need the concrete system change you want evaluated rather than a bare opinion prompt.";
  }

  if (/^i need to be gay\b|^am i gay\b|^i am gay\b/i.test(normalized)) {
    return "That reads as personal rather than an engineering instruction. If you meant the product should feel queerer, brighter, or more expressive, say that directly and I will route design work for it.";
  }

  if (/(make|turn).*(system|ui|app|site|dashboard).*(gay|queer|pride|camp|rainbow)/i.test(normalized)) {
    return "If you want a visibly queer, high-expression product direction, that is actionable. I can route frontend work for color, typography, motion, copy tone, and iconography instead of forcing a generic engineering plan.";
  }

  if (normalized.length < 24) {
    return view
      ? `I'm here. If you want, I can answer directly, inspect ${formatRoots(view.evidenceBundle?.matchedRoots ?? summarizeRoots(view))}, or start working on a concrete goal.`
      : "I'm here. Ask a question, describe a goal, or tell me what you want done, and I'll decide whether this should stay in chat or need execution.";
  }

  return "I can handle that directly here, or if it needs real execution I'll start working on it.";
}

function makeTask(
  goalId: string,
  input: Partial<CreateTaskInput> & Pick<CreateTaskInput, "title" | "description" | "role" | "taskType">
): CreateTaskInput {
  return {
    goalId,
    title: input.title,
    description: input.description,
    role: input.role,
    taskType: input.taskType,
    status: input.status ?? "backlog",
    agentMode: input.agentMode ?? "single",
    delegationPolicy: input.delegationPolicy ?? "single",
    locality: input.locality ?? "local",
    runtimeCandidates: input.runtimeCandidates ?? ["codex-local", "claude", "gemini", "opencode", "codex-cloud", "cursor", "generic"],
    providerCandidates: input.providerCandidates ?? ["openai", "anthropic", "google", "opencode", "cursor", "generic"],
    preferredRuntime: input.preferredRuntime ?? null,
    preferredProvider: input.preferredProvider ?? null,
    ownedFiles: input.ownedFiles ?? [],
    readOnlyPaths: input.readOnlyPaths ?? [],
    verificationPolicy: input.verificationPolicy ?? ["diff_sanity"],
    dependencies: input.dependencies ?? [],
    tokenBudget: {
      ...DEFAULT_TOKEN_BUDGET
    },
    constraints: input.constraints ?? {}
  };
}

function summarizeTopic(message: string): string {
  const normalized = normalizeMessage(message);
  return normalized.split(" ").slice(0, 10).join(" ");
}

function normalizeMessage(message: string): string {
  return message.trim().replace(/\s+/g, " ");
}

function isGreeting(message: string): boolean {
  return /^(hi|hello|hey|yo|sup|hiya|good morning|good afternoon|good evening)\b[!. ]*$/i.test(message);
}

function isAcknowledgement(message: string): boolean {
  return /^(ok|okay|cool|nice|thanks|thank you|yep|yeah|sure|sounds good)\b[!. ]*$/i.test(message);
}

function inferIntent(message: string): string {
  if (/analy[sz]e|analysis|inspect|discovery|architecture review|repo analysis|assess(ment)?( project| codebase| repo)?/i.test(message)) {
    return "discover";
  }
  if (/(test|validate|verify|check).*(pdf|ingest|parser|extract|ocr|accuracy)/i.test(message)) {
    return "verify";
  }
  if (/fix|bug|repair|broken|harden|accuracy/i.test(message)) {
    return "repair";
  }
  if (/refactor|rework|reshape/i.test(message)) {
    return "refactor";
  }
  if (/build|implement|create|scaffold|make|plan|route|decompose/i.test(message)) {
    return "build";
  }
  if (/review|audit|verify/i.test(message)) {
    return "review";
  }
  return "general";
}

function isAssessmentQuery(message: string): boolean {
  return /how('?s| is).*(system|app|project|repo)|status|current state|where are we|how.*looking/i.test(message);
}

/**
 * Clarification is only used when all are true:
 * - workspace snapshot exists,
 * - request is not already a discovery/PDF verification path,
 * - request is work-like but lacks matching evidence for the inferred domain.
 */
function shouldClarifyAgainstWorkspace(profile: RequestProfile, projectSnapshot: ProjectSnapshot | null): boolean {
  if (!projectSnapshot) {
    return false;
  }
  if (profile.discoveryRequest || profile.repoDiscoveryRequest || profile.pdfVerificationRequest || profile.localInspectionRequest) {
    return false;
  }
  if (!profile.explicitWorkRequest || profile.domain === "general" || profile.actionableThemeRequest) {
    return false;
  }
  return projectSnapshot.queryTerms.length > 0 && projectSnapshot.evidenceMatches.length === 0;
}

/**
 * Delegation policy:
 * - Always delegate explicit repo discovery and PDF verification intents.
 * - Keep personal/non-engineering prompts as direct responses.
 * - For question-form prompts, still delegate when they are actionable and repo-grounded.
 */
function shouldDelegate(profile: RequestProfile): boolean {
  if (profile.personal) {
    return false;
  }
  if (profile.repoDiscoveryRequest) {
    return true;
  }
  if (profile.discoveryRequest || profile.pdfVerificationRequest || profile.localInspectionRequest) {
    return true;
  }
  if (
    profile.questionOnly &&
    !profile.actionableThemeRequest &&
    !profile.explicitWorkRequest &&
    !profile.repoDiscoveryRequest &&
    !profile.discoveryRequest &&
    !profile.pdfVerificationRequest &&
    !profile.localInspectionRequest
  ) {
    return false;
  }
  return profile.explicitWorkRequest || profile.actionableThemeRequest;
}

/**
 * Request profiling is the central classifier used by delegation and slice shaping.
 *
 * Current behavior highlights:
 * - Vague but valid repo-grounded asks are interpreted as discovery.
 * - PDF accuracy/parsing requests are interpreted as verification/discovery lanes.
 * - Discovery-only asks default to read-only delegation without implementation slices.
 */
function buildRequestProfile(message: string): RequestProfile {
  const normalized = normalizeMessage(message);
  const lower = normalized.toLowerCase();
  const domain = inferDomain(lower);
  const discoveryRequest =
    /(repo analysis|analy[sz]e (the )?(repo|codebase|project)|inspect (the )?(repo|codebase|project)|architecture review|assess (the )?(project|repo|codebase)|run repo analysis|survey the codebase|look (through|around) (the )?(repo|codebase|project)|understand (the )?(repo|codebase|project|architecture)|deep dive (the )?(repo|codebase|project))/i.test(
      normalized
    );
  const repoDiscoveryRequest =
    /(repo|codebase|project|architecture).*(analy[sz]e|inspect|review|assess|scan|survey|explore|map|understand|look through|look around|deep dive|audit)|\b(use agents to )?(run )?(repo|codebase|project) (analysis|review|audit)\b/i.test(
      normalized
    );
  const pdfVerificationRequest =
    /(test|validate|verify|check|assess).*(pdf|document).*(accuracy|extraction|parser|parsing|ingestion|ocr)|(pdf|document).*(accuracy|extraction|parsing|parser).*(test|validate|verify|check)|test pdf accuracy|validate pdf extraction|check pdf parsing/i.test(
      normalized
    );
  const localInspectionRequest =
    ((/(list|show|find|locate|scan|check|inspect|what(?:'s| is| are)?|which)\b/i.test(normalized) &&
      /(nvme|ssd|disk|drive|filesystem|folder|directory|path|models?|checkpoints?|weights?|files?|repos?|projects?|\/|\.\.?\/)/i.test(
        normalized
      )) ||
      (/(size|space|usage|du|how big|how large)\b/i.test(normalized) &&
        /(repo|repository|project|workspace|folder|directory|disk|drive|nvme|ssd|filesystem)\b/i.test(normalized)));
  const queerVisualDirection = /(gay|queer|pride|camp|rainbow)/i.test(normalized);
  const actionableThemeRequest = queerVisualDirection && /(system|ui|app|site|dashboard|frontend|theme|look|brand)/i.test(normalized);
  const personal = /^i need to be gay\b|^am i gay\b|^i am gay\b/i.test(normalized);
  const questionOnly = /\?$/.test(normalized) || /^(what do you think|what u think|thoughts|opinion)\b/i.test(normalized);
  const implementationHeavyRequest =
    /(build|implement|create|fix|repair|refactor|rework|harden|improve|make|add|update)/i.test(normalized);
  const explicitWorkRequest =
    (/(build|implement|create|fix|repair|refactor|rework|harden|improve|make|add|update|audit|review|verify|plan|route|decompose|analy[sz]e|inspect|assess|scan|survey|explore|map|understand|look through|look around|deep dive)/i.test(
      normalized
    ) ||
      discoveryRequest ||
      repoDiscoveryRequest ||
      pdfVerificationRequest ||
      localInspectionRequest) &&
    !personal;
  const wantsFrontend =
    actionableThemeRequest ||
    /(ui|ux|frontend|dashboard|kanban|chat pane|web|visual|theme|brand|look|feel)/i.test(normalized) ||
    domain === "ui";
  const wantsDocs = /(docs|documentation|readme|adr)/i.test(normalized);
  const discoveryOnly =
    (discoveryRequest || repoDiscoveryRequest || pdfVerificationRequest || localInspectionRequest) &&
    !implementationHeavyRequest &&
    !wantsFrontend &&
    !wantsDocs;
  const wantsBackend =
    domain === "ingestion" ||
    repoDiscoveryRequest ||
    discoveryRequest ||
    pdfVerificationRequest ||
    /(backend|server|router|scheduler|janitor|parser|ingest|ingestion|extract|ocr|accuracy|pipeline|api)/i.test(normalized) ||
    (!wantsFrontend && !wantsDocs);

  return {
    intent: inferIntent(normalized),
    domain,
    explicitWorkRequest,
    discoveryRequest,
    repoDiscoveryRequest,
    pdfVerificationRequest,
    localInspectionRequest,
    discoveryOnly,
    questionOnly,
    personal,
    queerVisualDirection,
    actionableThemeRequest,
    wantsFrontend,
    wantsBackend,
    wantsDocs
  };
}

function inferDomain(message: string): RequestProfile["domain"] {
  if (/(pdf|ingest|ingestion|parser|extract|ocr|accuracy)/i.test(message)) {
    return "ingestion";
  }
  if (/(ui|ux|frontend|dashboard|kanban|visual|theme|brand|layout)/i.test(message)) {
    return "ui";
  }
  if (/(docs|readme|adr)/i.test(message)) {
    return "docs";
  }
  return "general";
}

function toWorkspaceSnapshot(projectSnapshot?: ProjectSnapshot | null): StrategistWorkspaceSnapshot | null {
  return projectSnapshot ? (projectSnapshot as StrategistWorkspaceSnapshot) : null;
}

function summarizeRoots(view: StrategistWorkspaceSnapshot): Array<{
  path: string;
  name: string;
  kind: ProjectSnapshot["projects"][number]["kind"];
  confidence: number;
  reason: string;
}> {
  return view.projects
    .map((project) => ({
      path: project.path,
      name: project.name,
      kind: project.kind,
      confidence: project.path === "." ? 0.32 : 0.5,
      reason: project.summary
    }))
    .slice(0, 3);
}

function summarizeFiles(view: StrategistWorkspaceSnapshot): Array<{
  path: string;
  score: number;
  reason: string;
}> {
  const candidates = [...view.evidenceMatches];
  if (view.dirtyFiles.length > 0) {
    for (const dirtyPath of view.dirtyFiles.slice(0, 3)) {
      candidates.unshift({ path: dirtyPath, term: "dirty" });
    }
  }
  return candidates.slice(0, 5).map((entry, index) => ({
    path: entry.path,
    score: 10 - index,
    reason: entry.term === "dirty" ? "dirty working tree file" : `query match for ${entry.term}`
  }));
}

function formatRoots(
  roots: Array<{
    path: string;
    name: string;
    kind: ProjectSnapshot["projects"][number]["kind"];
    confidence: number;
    reason: string;
  }>
): string {
  return roots
    .slice(0, 3)
    .map((root) => `${root.name} (${Math.round(root.confidence * 100)}%, ${root.reason})`)
    .join("; ");
}

function formatFiles(
  files: Array<{
    path: string;
    score: number;
    reason: string;
  }>
): string {
  return files
    .slice(0, 3)
    .map((file) => `${file.path} (${file.reason})`)
    .join(", ");
}

function summarizeRuntimeHealth(view: StrategistWorkspaceSnapshot): string {
  const runtimeHealth = view.runtimeHealth ?? [];
  const ready = runtimeHealth.filter((runtime) => runtime.status === "ready").map((runtime) => runtime.runtime);
  const degraded = runtimeHealth.filter((runtime) => runtime.status !== "ready");
  const readyLine = ready.length > 0 ? `ready: ${ready.join(", ")}` : "ready: none";
  const degradedLine =
    degraded.length > 0
      ? `degraded: ${degraded
          .slice(0, 4)
          .map((runtime) => `${runtime.runtime} (${runtime.status})`)
          .join(", ")}`
      : "degraded: none";
  return `${readyLine}; ${degradedLine}`;
}

function summarizeRiskLine(view: StrategistWorkspaceSnapshot): string {
  const risks: string[] = [];
  if (view.dirtyFiles.length > 0) {
    risks.push(`${view.dirtyFiles.length} dirty paths`);
  }
  if (view.operationalHealth.failedTasks > 0) {
    risks.push(`${view.operationalHealth.failedTasks} failed tasks`);
  }
  if (!view.verificationFreshness || view.verificationFreshness.freshnessBand === "unknown") {
    risks.push("no fresh verification");
  } else if (view.verificationFreshness.freshnessBand === "stale") {
    risks.push("verification is stale");
  }
  if (view.runtimeHealth?.some((runtime) => runtime.status !== "ready")) {
    risks.push("some runtimes are degraded");
  }
  return risks.length > 0 ? risks.join("; ") : "no obvious health blockers";
}

function chooseNextAssessmentStep(view: StrategistWorkspaceSnapshot): string {
  if (view.activeRoot?.path === "financial-engine_v2") {
    if (view.verificationFreshness?.freshnessBand !== "fresh") {
      return "inspect the latest PDF ingestion failure or run the deterministic verification path before calling it healthy";
    }
    return "inspect the ingestion path around the latest matched files and compare against the fresh verification result";
  }
  if (view.operationalHealth.failedTasks > 0) {
    const failure = view.operationalHealth.latestFailures[0];
    return failure ? `open the latest failed task, ${failure.title}, before broadening scope` : "open the latest failed task before broadening scope";
  }
  if (view.verificationFreshness?.freshnessBand === "unknown") {
    return "run deterministic verification before making a health claim";
  }
  return `use ${view.activeRoot?.name ?? "the active root"} as the next focused slice`;
}

function extractLastActionableTopic(conversation?: StrategistConversation): string | null {
  if (!conversation) {
    return null;
  }
  const priorUserMessages = [...conversation.messages]
    .filter((message) => message.role === "user")
    .map((message) => message.content.trim())
    .filter((content) => content.length > 0);
  for (let index = priorUserMessages.length - 1; index >= 0; index -= 1) {
    const candidate = priorUserMessages[index];
    if (!candidate) {
      continue;
    }
    if (/(build|implement|create|fix|repair|refactor|rework|harden|improve|make|add|update|audit|review|verify|plan|route|decompose|pdf|ingest|ui|frontend|backend)/i.test(candidate)) {
      return candidate;
    }
  }
  return null;
}

function deriveOwnedFiles(projectSnapshot: ProjectSnapshot | null, domain: RequestProfile["domain"]): string[] {
  if (!projectSnapshot || domain !== "ingestion") {
    return [];
  }
  const paths = projectSnapshot.evidenceMatches.map((match) => match.path);
  const globs = new Set<string>();
  for (const evidencePath of paths) {
    if (evidencePath.startsWith("financial-engine_v2/scripts/")) {
      globs.add("financial-engine_v2/scripts/**");
    } else if (evidencePath.startsWith("financial-engine_v2/backend/")) {
      globs.add("financial-engine_v2/backend/**");
    } else if (evidencePath.startsWith("docs/")) {
      globs.add(evidencePath);
    }
  }
  return [...globs];
}

function deriveReadOnlyPaths(projectSnapshot: ProjectSnapshot | null, domain: RequestProfile["domain"]): string[] {
  if (!projectSnapshot || domain !== "ingestion") {
    return [];
  }
  const readPaths = new Set<string>();
  for (const evidencePath of projectSnapshot.evidenceMatches.map((match) => match.path)) {
    if (evidencePath.startsWith("financial-engine_v2/")) {
      readPaths.add("financial-engine_v2/**");
    } else if (evidencePath.startsWith("docs/")) {
      readPaths.add("docs/**");
    } else if (evidencePath.startsWith("reports/")) {
      readPaths.add("reports/**");
    }
  }
  return [...readPaths];
}

interface RequestProfile {
  intent: string;
  domain: "ingestion" | "ui" | "docs" | "general";
  explicitWorkRequest: boolean;
  discoveryRequest: boolean;
  // Broader repo/codebase investigation signals, including vague-but-actionable asks.
  repoDiscoveryRequest: boolean;
  // PDF validation/extraction/parsing accuracy signals.
  pdfVerificationRequest: boolean;
  // Concrete read-only local inspection asks such as files/models/paths/drives.
  localInspectionRequest: boolean;
  // True when strategist should route discovery/review only (no implementation slices).
  discoveryOnly: boolean;
  questionOnly: boolean;
  personal: boolean;
  queerVisualDirection: boolean;
  actionableThemeRequest: boolean;
  wantsFrontend: boolean;
  wantsBackend: boolean;
  wantsDocs: boolean;
}

interface SliceTemplate {
  localKey: string;
  title: string;
  description: string;
  role: "worker" | "reviewer" | "strategist";
  taskType: TaskType;
  delegationPolicy: CreateTaskInput["delegationPolicy"];
  runtimeCandidates: RuntimeId[];
  providerCandidates: CreateTaskInput["providerCandidates"];
  ownedFiles: string[];
  readOnlyPaths: string[];
  verificationPolicy: CreateTaskInput["verificationPolicy"];
  constraints: CreateTaskInput["constraints"];
  dependsOnLocalKeys: string[];
}

export function materializeTaskGraph(plan: StrategistPlan): { rootTask: TaskRecord | null; childTasks: TaskRecord[] } {
  if (!plan.rootTask) {
    return { rootTask: null, childTasks: [] };
  }

  const now = nowIso();
  const rootId = createId("task");
  const rootTask = createTaskRecord(rootId, plan.rootTask, null, now);
  const childTasks: TaskRecord[] = [];
  const taskIdsByLocalKey = new Map<string, string>();

  for (const nextInput of plan.childTasks) {
    const taskId = createId("task");
    taskIdsByLocalKey.set(nextInput.localKey, taskId);
  }

  for (const nextInput of plan.childTasks) {
    const taskId = taskIdsByLocalKey.get(nextInput.localKey);
    if (!taskId) {
      continue;
    }
    const record = createTaskRecord(taskId, nextInput, rootId, now);
    record.dependencies = nextInput.dependsOnLocalKeys
      .map((localKey) => taskIdsByLocalKey.get(localKey))
      .filter((dependencyId): dependencyId is string => Boolean(dependencyId));
    record.status = record.dependencies.length === 0 ? "ready" : "backlog";
    childTasks.push(record);
  }

  return { rootTask, childTasks };
}

function createTaskRecord(id: string, input: CreateTaskInput, parentId: string | null, timestamp: string): TaskRecord {
  return {
    id,
    goalId: input.goalId,
    parentId,
    title: input.title,
    description: input.description,
    status: input.status ?? "backlog",
    role: input.role,
    taskType: input.taskType,
    agentMode: input.agentMode ?? "single",
    delegationPolicy: input.delegationPolicy ?? "single",
    locality: input.locality ?? "local",
    runtimeCandidates: input.runtimeCandidates ?? [],
    providerCandidates: input.providerCandidates ?? [],
    preferredRuntime: input.preferredRuntime ?? null,
    preferredProvider: input.preferredProvider ?? null,
    chosenRuntime: null,
    chosenProvider: null,
    chosenModel: null,
    ownedFiles: input.ownedFiles ?? [],
    readOnlyPaths: input.readOnlyPaths ?? [],
    verificationPolicy: input.verificationPolicy ?? ["diff_sanity"],
    tokenBudget: {
      ...DEFAULT_TOKEN_BUDGET,
      ...(input.tokenBudget ?? {})
    },
    dependencies: input.dependencies ?? [],
    attempts: 0,
    maxAttempts: 3,
    routingRationale: null,
    constraints: input.constraints ?? {},
    createdAt: timestamp,
    updatedAt: timestamp
  };
}

interface StrategistChildTaskInput extends CreateTaskInput {
  localKey: string;
  dependsOnLocalKeys: string[];
}
