import type { ProviderCapabilitySnapshot, StrategistConversation } from "../../shared/types";
import { runCommand, type CommandResult } from "../utils/process";

export interface StrategistLlmInput {
  message: string;
  fallbackReply: string;
  mode: "respond" | "delegate";
  cwd: string;
  capabilities: ProviderCapabilitySnapshot[];
  conversation?: StrategistConversation;
  projectSummary?: string | null;
}

type StrategistRuntime = "codex-local" | "claude" | "gemini";

export class StrategistLlmResponder {
  constructor(
    private readonly commandRunner: typeof runCommand = runCommand
  ) {}

  async generateReply(input: StrategistLlmInput): Promise<string> {
    const runtime = pickStrategistRuntime(input.capabilities);
    if (!runtime) {
      return input.fallbackReply;
    }

    const command = resolveCommand(runtime, input.capabilities);
    if (!command) {
      return input.fallbackReply;
    }

    const prompt = buildPrompt(input);
    const result = await this.commandRunner(command, buildArgs(runtime, input.cwd, prompt), {
      cwd: input.cwd,
      env: process.env,
      timeoutMs: 60_000
    });
    if (!result.ok) {
      return input.fallbackReply;
    }
    const parsed = parseReply(runtime, result);
    return parsed ?? input.fallbackReply;
  }
}

function pickStrategistRuntime(capabilities: ProviderCapabilitySnapshot[]): StrategistRuntime | null {
  const preferred = (process.env.STRATEGIST_CHAT_RUNTIME?.trim() ?? "") as StrategistRuntime | "";
  if (!preferred) {
    return null;
  }
  const ordered: StrategistRuntime[] = preferred
    ? [preferred, "claude", "gemini", "codex-local"]
    : ["claude", "gemini", "codex-local"];

  for (const runtime of ordered) {
    const capability = capabilities.find((candidate) => candidate.runtime === runtime);
    if (!capability) {
      continue;
    }
    if (capability.installStatus === "installed" && capability.authStatus === "authenticated" && capability.command) {
      return runtime;
    }
  }
  return null;
}

function resolveCommand(runtime: StrategistRuntime, capabilities: ProviderCapabilitySnapshot[]): string | null {
  return capabilities.find((candidate) => candidate.runtime === runtime)?.command ?? null;
}

function buildArgs(runtime: StrategistRuntime, cwd: string, prompt: string): string[] {
  if (runtime === "codex-local") {
    return ["exec", "--cd", cwd, "--sandbox", "read-only", "--skip-git-repo-check", "--", prompt];
  }
  if (runtime === "claude") {
    return ["-p", "--permission-mode", "plan", prompt];
  }
  return ["-p", prompt];
}

function buildPrompt(input: StrategistLlmInput): string {
  const recentConversation = input.conversation?.messages.slice(-6).map((message) => `${message.role}: ${message.content}`).join("\n") ?? "none";
  const workspaceSummary = input.projectSummary?.trim() || "No fresh workspace summary available.";
  const modeLine =
    input.mode === "delegate"
      ? "Execution is being delegated. Explain the next step naturally and mention that tasks are being created, but do not invent task ids or internal implementation details."
      : "Answer directly in chat. Do not suggest a repo scan unless the user actually asked for one.";

  return [
    "You are the chat-facing assistant inside a coding orchestrator.",
    "Be natural, concise, and human. Sound like a real assistant, not a rules engine.",
    "Do not mention confidence percentages, dirty files, active roots, or internal evidence scoring unless the user explicitly asks.",
    modeLine,
    "If the user is just greeting or making small talk, reply like a normal assistant.",
    "If there is relevant workspace context, use it quietly and only when it helps.",
    "",
    `Workspace summary:\n${workspaceSummary}`,
    "",
    `Recent conversation:\n${recentConversation}`,
    "",
    `User message:\n${input.message}`,
    "",
    `Fallback draft reply:\n${input.fallbackReply}`,
    "",
    "Return only the assistant reply text."
  ].join("\n");
}

function parseReply(runtime: StrategistRuntime, result: CommandResult): string | null {
  const raw = sanitizeReply(`${result.stdout}\n${result.stderr}`);
  if (!raw) {
    return null;
  }

  if (runtime === "claude") {
    return parseClaudeReply(raw) ?? raw;
  }

  return raw;
}

function parseClaudeReply(raw: string): string | null {
  const lines = raw.split("\n").map((line) => line.trim()).filter(Boolean);
  const parts: string[] = [];
  for (const line of lines) {
    try {
      const parsed = JSON.parse(line) as Record<string, unknown>;
      const type = typeof parsed.type === "string" ? parsed.type : "";
      if (type === "content_block_delta") {
        const delta = parsed.delta;
        if (delta && typeof delta === "object" && "text" in delta && typeof (delta as { text?: unknown }).text === "string") {
          parts.push((delta as { text: string }).text);
        }
      }
      if (type === "message" && typeof parsed.content === "string") {
        parts.push(parsed.content);
      }
    } catch {
      continue;
    }
  }
  const combined = parts.join("").trim();
  return combined.length > 0 ? combined : null;
}

function sanitizeReply(raw: string): string | null {
  const cleaned = raw
    .split("\n")
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return false;
      }
      if (/^202\d-.*\bERROR\b/i.test(trimmed)) {
        return false;
      }
      if (/^Reading additional input from stdin/i.test(trimmed)) {
        return false;
      }
      if (/^OpenAI Codex v/i.test(trimmed)) {
        return false;
      }
      if (/^workdir:/i.test(trimmed) || /^model:/i.test(trimmed) || /^provider:/i.test(trimmed) || /^approval:/i.test(trimmed) || /^sandbox:/i.test(trimmed) || /^reasoning effort:/i.test(trimmed) || /^reasoning summaries:/i.test(trimmed) || /^session id:/i.test(trimmed)) {
        return false;
      }
      if (/^\[ERROR\]/i.test(trimmed) || /^Keychain initialization/i.test(trimmed) || /^Using FileKeychain/i.test(trimmed) || /^Loaded cached credentials/i.test(trimmed)) {
        return false;
      }
      if (/^user$/i.test(trimmed) || /^assistant$/i.test(trimmed)) {
        return false;
      }
      if (/^-{4,}$/.test(trimmed)) {
        return false;
      }
      return true;
    })
    .join("\n")
    .replace(/\u001b\[[0-9;]*m/g, "")
    .trim();
  return cleaned.length > 0 ? cleaned : null;
}
