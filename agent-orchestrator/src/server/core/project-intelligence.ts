import fs from "fs";
import path from "path";

import type {
  OperationalHealthSnapshot,
  ProjectEvidenceMatch,
  ProjectRootSummary,
  ProjectSnapshot,
  ProviderCapabilitySnapshot,
  RuntimeId
} from "../../shared/types";
import type { StoreCollections } from "../db/database";
import { runCommand } from "../utils/process";
import { nowIso } from "../utils/time";

export interface StrategistWorkspaceContext {
  snapshot: StrategistProjectSnapshot;
  hasMatchingEvidence: boolean;
}

export interface StrategistProjectSnapshot extends ProjectSnapshot {
  activeRoot: ActiveRootGuess;
  verificationFreshness: VerificationFreshness;
  runtimeHealth: RuntimeHealthRecord[];
  evidenceBundle: StrategistEvidenceBundle;
  workspaceLexicon: string[];
}

interface ActiveRootGuess {
  path: string;
  name: string;
  kind: ProjectRootSummary["kind"];
  confidence: number;
  reason: string;
}

interface VerificationFreshness {
  freshnessBand: "fresh" | "warm" | "stale" | "unknown";
  lastPassedAt: string | null;
  lastFailedAt: string | null;
  summary: string;
}

interface RuntimeHealthRecord {
  runtime: RuntimeId;
  provider: ProviderCapabilitySnapshot["provider"];
  installStatus: ProviderCapabilitySnapshot["installStatus"];
  authStatus: ProviderCapabilitySnapshot["authStatus"];
  detectedAt: string;
  status: "ready" | "needs_auth" | "missing" | "unsupported" | "degraded";
  ageMinutes: number;
  notes: string[];
}

interface StrategistEvidenceBundle {
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
}

const STOP_WORDS = new Set([
  "the",
  "and",
  "for",
  "with",
  "from",
  "this",
  "that",
  "what",
  "hows",
  "how",
  "system",
  "looking",
  "need",
  "make",
  "whole",
  "project",
  "codebase",
  "repo",
  "status",
  "state",
  "please"
]);

const QUERY_LEXICON: Record<string, string[]> = {
  pdf: ["pdf", "ingestion", "ingest", "extract", "parser", "ocr", "marketindex"],
  ingest: ["ingest", "ingestion", "pdf", "extract", "parser", "ocr"],
  ingestion: ["ingestion", "ingest", "pdf", "extract", "parser", "ocr"],
  extract: ["extract", "extraction", "parser", "ocr", "pdf"],
  parser: ["parser", "parse", "extract", "pdf", "ocr"],
  ocr: ["ocr", "extract", "parser", "pdf"],
  accuracy: ["accuracy", "quality", "eval", "evaluation", "verify", "verification"],
  orchestrator: ["orchestrator", "router", "scheduler", "task", "janitor", "worktree"],
  router: ["router", "routing", "dispatch", "scheduler", "task"],
  scheduler: ["scheduler", "queue", "dispatch", "task"],
  task: ["task", "queue", "board", "session", "run"],
  ui: ["ui", "frontend", "kanban", "dashboard", "chat", "workspace"],
  frontend: ["frontend", "ui", "kanban", "dashboard", "chat"],
  docs: ["docs", "documentation", "readme", "adr", "snapshot"],
  status: ["status", "health", "verification", "runtime", "tasks"],
  system: ["system", "workspace", "repo", "health", "status"]
};

export class ProjectIntelligenceService {
  private cachedFileIndex: { generatedAt: number; files: string[] } | null = null;

  constructor(private readonly repoRoot: string) {}

  async getStrategistContext(collections: StoreCollections, query?: string): Promise<StrategistWorkspaceContext> {
    const snapshot = await this.buildSnapshot(collections, query);
    return {
      hasMatchingEvidence: snapshot.evidenceMatches.length > 0,
      snapshot
    };
  }

  async buildSnapshot(collections: StoreCollections, query?: string): Promise<StrategistProjectSnapshot> {
    const [dirtyFiles, fileIndex] = await Promise.all([this.getDirtyFiles(), this.getFileIndex()]);
    const queryTerms = extractQueryTerms(query);
    const evidenceMatches = matchEvidence(queryTerms, fileIndex);
    const projects = this.buildProjectSummaries();
    const activeRoot = inferActiveRoot(projects, dirtyFiles, evidenceMatches, queryTerms);
    const verificationFreshness = buildVerificationFreshness(collections);
    const runtimeHealth = buildRuntimeHealth(collections);
    const evidenceBundle = buildEvidenceBundle(projects, dirtyFiles, evidenceMatches, activeRoot, runtimeHealth, verificationFreshness);
    const workspaceLexicon = buildWorkspaceLexicon(projects);

    return {
      generatedAt: nowIso(),
      repoRoot: this.repoRoot,
      projects,
      dirtyFiles,
      evidenceMatches,
      queryTerms,
      operationalHealth: buildOperationalHealth(collections),
      activeRoot,
      verificationFreshness,
      runtimeHealth,
      evidenceBundle,
      workspaceLexicon
    };
  }

  private buildProjectSummaries(): ProjectRootSummary[] {
    const summaries: ProjectRootSummary[] = [];

    const workspaceReadme = readText(path.join(this.repoRoot, "README.md"));
    summaries.push({
      path: ".",
      kind: "workspace",
      name: "TENN workspace",
      summary:
        clampSummary(
          extractActiveRuntimeSummary(workspaceReadme) ??
            firstSentence(workspaceReadme) ??
            "Multi-project workspace with an active runtime and supporting apps."
        ) ??
        "Multi-project workspace with an active runtime and supporting apps.",
      keyFiles: ["README.md", "docs/current_system.md", "run.py"]
    });

    const financialReadme = readText(path.join(this.repoRoot, "financial-engine_v2", "README.md"));
    if (financialReadme) {
      summaries.push({
        path: "financial-engine_v2",
        kind: "python",
        name: "Financial Engine v2",
        summary:
          clampSummary(
            extractSectionParagraph(financialReadme, "## Objective") ??
              firstSentence(financialReadme) ??
              "Local-first ingestion, retrieval, and extraction pipeline for ASX periodic documents."
          ) ??
          "Local-first ingestion, retrieval, and extraction pipeline for ASX periodic documents.",
        keyFiles: [
          "financial-engine_v2/README.md",
          "financial-engine_v2/scripts/marketindex_ingest.py",
          "financial-engine_v2/scripts/marketindex_download_pdfs.py",
          "financial-engine_v2/backend/app/services/text_extract.py"
        ]
      });
    }

    const orchestratorReadme = readText(path.join(this.repoRoot, "agent-orchestrator", "README.md"));
    if (orchestratorReadme) {
      summaries.push({
        path: "agent-orchestrator",
        kind: "node",
        name: "Agent Orchestrator",
        summary: "Local-agent-first orchestration control plane with strategist chat, routed child tasks, worktree isolation, and deterministic review gates.",
        keyFiles: [
          "agent-orchestrator/README.md",
          "agent-orchestrator/src/server/services/orchestrator.ts",
          "agent-orchestrator/src/server/core/router.ts",
          "agent-orchestrator/src/web/App.tsx"
        ]
      });
    }

    const marketIndexSnapshot = readText(path.join(this.repoRoot, "docs", "marketindex_architecture_snapshot.md"));
    if (marketIndexSnapshot) {
      summaries.push({
        path: "docs/marketindex_architecture_snapshot.md",
        kind: "docs",
        name: "Legacy MarketIndex PDF pipeline",
        summary: "Archived reference for the older MarketIndex announcement scrape, PDF download, and daily orchestration flow.",
        keyFiles: [
          "docs/marketindex_architecture_snapshot.md",
          "scripts/archive/legacy_root_20260218/download_marketindex_pdfs.py",
          "reports/pdf_download_report.json"
        ]
      });
    }

    return summaries;
  }

  private async getDirtyFiles(): Promise<string[]> {
    const result = await runCommand("git", ["status", "--short"], { cwd: this.repoRoot });
    if (!result.ok || !result.stdout.trim()) {
      return [];
    }

  return result.stdout
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => (line.length > 3 ? line.slice(3).trim() : line.trim()))
      .filter((line) => line.length > 0)
      .filter((line) => path.basename(line) !== ".DS_Store")
      .slice(0, 12);
  }

  private async getFileIndex(): Promise<string[]> {
    if (this.cachedFileIndex && Date.now() - this.cachedFileIndex.generatedAt < 10_000) {
      return this.cachedFileIndex.files;
    }

    const result = await runCommand(
      "rg",
      [
        "--files",
        this.repoRoot,
        "-g",
        "!**/.git/**",
        "-g",
        "!**/node_modules/**",
        "-g",
        "!**/dist/**",
        "-g",
        "!**/.data/**",
        "-g",
        "!**/.tmp/**",
        "-g",
        "!**/venv/**",
        "-g",
        "!**/__pycache__/**"
      ],
      { cwd: this.repoRoot }
    );

    const files = result.ok
      ? result.stdout
          .split("\n")
          .map((line) => line.trim())
          .filter((line) => line.length > 0)
          .map((line) => path.relative(this.repoRoot, line))
      : [];

    this.cachedFileIndex = {
      generatedAt: Date.now(),
      files
    };
    return files;
  }
}

function readText(filePath: string): string | null {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return null;
  }
}

function extractActiveRuntimeSummary(text: string | null): string | null {
  if (!text) {
    return null;
  }
  const match = text.match(/active (?:runtime|system) (?:is )?`([^`]+)`/i);
  return match ? `Active runtime is ${match[1]}.` : null;
}

function extractSectionParagraph(text: string | null, heading: string): string | null {
  if (!text) {
    return null;
  }
  const start = text.indexOf(heading);
  if (start === -1) {
    return null;
  }
  const remainder = text.slice(start + heading.length).trim();
  const paragraph = remainder.split(/\n\s*\n/)[0]?.trim();
  return paragraph ? paragraph.replace(/\s+/g, " ") : null;
}

function firstSentence(text: string | null): string | null {
  if (!text) {
    return null;
  }
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return null;
  }
  const sentence = normalized.match(/(.+?[.?!])(\s|$)/);
  return sentence?.[1] ?? normalized.slice(0, 180);
}

function clampSummary(text: string | null, maxLength = 180): string | null {
  if (!text) {
    return null;
  }
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 1).trim()}...`;
}

function inferActiveRoot(
  projects: ProjectRootSummary[],
  dirtyFiles: string[],
  evidenceMatches: ProjectEvidenceMatch[],
  queryTerms: string[]
): ActiveRootGuess {
  const scored = projects
    .map((project) => {
      const signals: string[] = [];
      let score = project.path === "." ? 0 : 1;

      const dirtyHits = dirtyFiles.filter((file) => matchesProjectScope(project, file));
      if (dirtyHits.length > 0) {
        score += 8 + dirtyHits.length;
        signals.push(`dirty files: ${dirtyHits.slice(0, 3).join(", ")}`);
      }

      const evidenceHits = evidenceMatches.filter((match) => matchesProjectScope(project, match.path));
      if (evidenceHits.length > 0) {
        score += 6 + evidenceHits.length;
        signals.push(`evidence: ${evidenceHits.slice(0, 3).map((match) => match.path).join(", ")}`);
      }

      const queryScore = scoreQueryAgainstProject(project, queryTerms);
      if (queryScore > 0) {
        score += queryScore;
        signals.push(`query: ${queryTerms.slice(0, 4).join(", ")}`);
      }

      return {
        project,
        score,
        reason: signals.length > 0 ? signals.join("; ") : "default workspace fallback"
      };
    })
    .sort((left, right) => right.score - left.score || left.project.path.length - right.project.path.length);

  const winner = scored[0];
  if (!winner || winner.score <= 0) {
    const fallback = projects.find((project) => project.path === ".") ?? projects[0];
    return {
      path: fallback?.path ?? ".",
      name: fallback?.name ?? "workspace",
      kind: fallback?.kind ?? "workspace",
      confidence: 0.24,
      reason: "no strong root evidence; defaulting to the workspace shell"
    };
  }

  return {
    path: winner.project.path,
    name: winner.project.name,
    kind: winner.project.kind,
    confidence: Math.min(0.96, 0.35 + winner.score / 20),
    reason: winner.reason
  };
}

function scoreQueryAgainstProject(project: ProjectRootSummary, queryTerms: string[]): number {
  if (queryTerms.length === 0) {
    return 0;
  }

  const joined = `${project.name} ${project.summary} ${project.keyFiles.join(" ")}`.toLowerCase();
  let score = 0;
  for (const term of queryTerms) {
    if (joined.includes(term)) {
      score += 2;
    }
  }

  if (project.path === "financial-engine_v2" && queryTerms.some((term) => /(pdf|ingest|ingestion|extract|ocr|accuracy)/.test(term))) {
    score += 6;
  }
  if (project.path === "agent-orchestrator" && queryTerms.some((term) => /(orchestrator|router|scheduler|task|kanban|strategy|agent)/.test(term))) {
    score += 6;
  }
  if (project.path.startsWith("docs") && queryTerms.some((term) => /(doc|docs|readme|adr|snapshot|arch)/.test(term))) {
    score += 4;
  }
  if (project.path === "." && queryTerms.some((term) => /(status|state|system|repo|workspace)/.test(term))) {
    score += 2;
  }

  return score;
}

function buildVerificationFreshness(collections: StoreCollections): VerificationFreshness {
  const sorted = [...collections.janitorResults].sort((left, right) => right.createdAt.localeCompare(left.createdAt));
  const latestPassed = sorted.find((result) => result.status === "passed") ?? null;
  const latestFailed = sorted.find((result) => result.status === "failed") ?? null;
  const now = Date.now();

  const summaryParts: string[] = [];
  if (latestPassed) {
    summaryParts.push(`last pass ${describeAge(latestPassed.createdAt, now)} on ${lookupTaskTitle(collections, latestPassed.taskId)}`);
  }
  if (latestFailed) {
    summaryParts.push(`last failure ${describeAge(latestFailed.createdAt, now)} on ${lookupTaskTitle(collections, latestFailed.taskId)}`);
  }
  if (summaryParts.length === 0) {
    summaryParts.push("no janitor verification has run yet");
  }

  const freshnessBand =
    latestPassed === null
      ? "unknown"
      : ageMinutes(latestPassed.createdAt, now) <= 60 * 24
        ? "fresh"
        : ageMinutes(latestPassed.createdAt, now) <= 60 * 24 * 7
          ? "warm"
          : "stale";

  return {
    freshnessBand,
    lastPassedAt: latestPassed?.createdAt ?? null,
    lastFailedAt: latestFailed?.createdAt ?? null,
    summary: summaryParts.join("; ")
  };
}

function buildRuntimeHealth(collections: StoreCollections): RuntimeHealthRecord[] {
  const now = Date.now();
  return [...collections.capabilities]
    .sort((left, right) => right.detectedAt.localeCompare(left.detectedAt) || left.runtime.localeCompare(right.runtime))
    .map((capability) => {
      const detectedAgeMinutes = ageMinutes(capability.detectedAt, now);
      const status =
        capability.installStatus !== "installed"
          ? "missing"
          : capability.authStatus === "authenticated"
            ? "ready"
            : capability.authStatus === "logged_out"
              ? "needs_auth"
              : capability.authStatus === "unsupported"
                ? "unsupported"
                : "degraded";
      const notes: string[] = [];
      if (capability.supportsNativeSubagents) {
        notes.push("native subagents");
      }
      if (capability.supportsCompaction) {
        notes.push("compaction");
      }
      if (capability.supportsCloud) {
        notes.push("cloud");
      }
      if (capability.supportsReadOnlyPlanMode) {
        notes.push("plan mode");
      }

      return {
        runtime: capability.runtime,
        provider: capability.provider,
        installStatus: capability.installStatus,
        authStatus: capability.authStatus,
        detectedAt: capability.detectedAt,
        status,
        ageMinutes: detectedAgeMinutes,
        notes
      };
    });
}

function buildEvidenceBundle(
  projects: ProjectRootSummary[],
  dirtyFiles: string[],
  evidenceMatches: ProjectEvidenceMatch[],
  activeRoot: ActiveRootGuess,
  runtimeHealth: RuntimeHealthRecord[],
  verificationFreshness: VerificationFreshness
): StrategistEvidenceBundle {
  const roots = projects
    .map((project) => {
      const dirtyHits = dirtyFiles.filter((file) => matchesProjectScope(project, file));
      const evidenceHits = evidenceMatches.filter((match) => matchesProjectScope(project, match.path));
      const score = dirtyHits.length * 4 + evidenceHits.length * 3 + (project.path === activeRoot.path ? 5 : 0);
      const reasons: string[] = [];
      if (dirtyHits.length > 0) {
        reasons.push(`dirty ${dirtyHits.slice(0, 2).join(", ")}`);
      }
      if (evidenceHits.length > 0) {
        reasons.push(`evidence ${evidenceHits.slice(0, 2).map((match) => match.path).join(", ")}`);
      }
      if (project.path === activeRoot.path) {
        reasons.push("active root");
      }
      return {
        path: project.path,
        name: project.name,
        kind: project.kind,
        confidence: Math.min(0.99, 0.3 + score / 15),
        reason: reasons.length > 0 ? reasons.join("; ") : "project root with no direct query evidence"
      };
    })
    .filter((entry) => entry.confidence > 0.3 || entry.path === activeRoot.path)
    .sort((left, right) => right.confidence - left.confidence || left.path.length - right.path.length)
    .slice(0, 3);

  const matchedFiles = [
    ...dirtyFiles.slice(0, 3).map((pathName) => ({
      path: pathName,
      score: 10,
      reason: "dirty working tree file"
    })),
    ...evidenceMatches.slice(0, 5).map((match, index) => ({
      path: match.path,
      score: 8 - index,
      reason: `query match for ${match.term}`
    }))
  ]
    .filter((entry, index, all) => all.findIndex((candidate) => candidate.path === entry.path) === index)
    .slice(0, 5);

  const signals = [
    `active-root: ${activeRoot.name} (${activeRoot.reason})`,
    `verification: ${verificationFreshness.summary}`,
    `runtimes: ${runtimeHealth.filter((runtime) => runtime.status === "ready").length} ready, ${runtimeHealth.filter((runtime) => runtime.status !== "ready").length} degraded`
  ];

  return {
    matchedRoots: roots,
    matchedFiles,
    signals
  };
}

function buildWorkspaceLexicon(projects: ProjectRootSummary[]): string[] {
  const hints = new Set<string>();
  for (const project of projects) {
    if (project.path === "financial-engine_v2") {
      hints.add("pdf ingestion -> financial-engine_v2");
      hints.add("marketindex -> financial-engine_v2/scripts/marketindex_download_pdfs.py");
      hints.add("extraction -> financial-engine_v2/backend/app/services/text_extract.py");
    }
    if (project.path === "agent-orchestrator") {
      hints.add("orchestrator -> agent-orchestrator");
      hints.add("router -> agent-orchestrator/src/server/core/router.ts");
      hints.add("kanban ui -> agent-orchestrator/src/web");
    }
  }
  return [...hints].slice(0, 8);
}

function matchesProjectScope(project: ProjectRootSummary, targetPath: string): boolean {
  if (project.path === ".") {
    return !targetPath.includes("/");
  }
  return targetPath === project.path || targetPath.startsWith(`${project.path}/`);
}

function ageMinutes(isoTimestamp: string, now: number): number {
  return Math.max(0, Math.round((now - new Date(isoTimestamp).getTime()) / 60000));
}

function describeAge(isoTimestamp: string, now: number): string {
  const minutes = ageMinutes(isoTimestamp, now);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 48) {
    return `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function lookupTaskTitle(collections: StoreCollections, taskId: string): string {
  return collections.tasks.find((task) => task.id === taskId)?.title ?? taskId;
}

function buildOperationalHealth(collections: StoreCollections): OperationalHealthSnapshot {
  const failedTasks = collections.tasks
    .filter((task) => task.status === "failed")
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .slice(0, 5)
    .map((task) => ({
      taskId: task.id,
      title: task.title,
      runtime: task.chosenRuntime,
      updatedAt: task.updatedAt
    }));

  return {
    totalTasks: collections.tasks.length,
    runningTasks: collections.tasks.filter((task) => task.status === "running").length,
    failedTasks: collections.tasks.filter((task) => task.status === "failed").length,
    blockedTasks: collections.tasks.filter((task) => task.status === "blocked").length,
    reviewTasks: collections.tasks.filter((task) => task.status === "review").length,
    liveSessions: collections.sessions.filter((session) => session.status === "running" || session.status === "waiting").length,
    authenticatedRuntimes: collections.capabilities
      .filter((capability) => capability.installStatus === "installed" && capability.authStatus === "authenticated")
      .map((capability) => capability.runtime),
    degradedRuntimes: collections.capabilities
      .filter((capability) => capability.installStatus !== "installed" || capability.authStatus === "logged_out")
      .map((capability) =>
        capability.installStatus !== "installed"
          ? `${capability.runtime} (${capability.installStatus})`
          : `${capability.runtime} (${capability.authStatus})`
      ),
    latestFailures: failedTasks
  };
}

function extractQueryTerms(query?: string): string[] {
  if (!query) {
    return [];
  }

  const tokens = query
    .toLowerCase()
    .split(/[^a-z0-9_/-]+/)
    .map((term) => term.trim())
    .filter((term) => term.length >= 3)
    .filter((term) => !STOP_WORDS.has(term));

  const expanded = tokens.flatMap((token) => [token, ...(QUERY_LEXICON[token] ?? [])]);
  return [...new Set(expanded)].slice(0, 10);
}

function matchEvidence(queryTerms: string[], fileIndex: string[]): ProjectEvidenceMatch[] {
  if (queryTerms.length === 0) {
    return [];
  }

  const scored = fileIndex
    .map((relativePath) => {
      const lowerPath = relativePath.toLowerCase();
      let score = 0;
      const matchedTerms: string[] = [];

      for (const term of queryTerms) {
        if (lowerPath.includes(term)) {
          matchedTerms.push(term);
          score += path.basename(lowerPath).includes(term) ? 4 : 2;
        }
      }

      score += scoreEvidencePath(lowerPath);

      return {
        path: relativePath,
        score,
        matchedTerms
      };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || left.path.length - right.path.length)
    .slice(0, 8);

  return scored.map((entry) => ({
    term: entry.matchedTerms[0] ?? queryTerms[0] ?? "query",
    path: entry.path
  }));
}

function scoreEvidencePath(relativePath: string): number {
  if (relativePath.startsWith("financial-engine_v2/scripts/")) {
    return 8;
  }
  if (relativePath.startsWith("financial-engine_v2/backend/")) {
    return 7;
  }
  if (relativePath.startsWith("agent-orchestrator/src/")) {
    return 6;
  }
  if (relativePath.startsWith("docs/")) {
    return 5;
  }
  if (relativePath.startsWith("reports/")) {
    return -2;
  }
  if (relativePath.includes("/archive/")) {
    return -4;
  }
  return 0;
}
