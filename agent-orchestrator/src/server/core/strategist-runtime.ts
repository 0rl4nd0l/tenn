import type { ProviderCapabilitySnapshot, StrategistConversation } from "../../shared/types";
import { spawnCommand } from "../utils/process";

export interface StrategistRuntimeInput {
  message: string;
  fallbackReply: string;
  cwd: string;
  capabilities: ProviderCapabilitySnapshot[];
  conversation: StrategistConversation;
  projectSummary?: string | null;
  sessionId?: string | null;
  preferredRuntime?: "codex-local" | "opencode" | null;
  preferredModel?: string | null;
}

export interface StrategistRuntimeCallbacks {
  onDelta: (delta: string) => void;
  onComplete: (reply: string) => void;
  onError: (message: string) => void;
  onSessionStarted?: (sessionId: string) => void;
}

interface RuntimeSelection {
  runtime: "codex-local" | "opencode";
  command: string;
  model: string | null;
}

export class StrategistRuntimeRunner {
  constructor(
    private readonly spawnRunner: typeof spawnCommand = spawnCommand
  ) {}

  run(input: StrategistRuntimeInput, callbacks: StrategistRuntimeCallbacks): void {
    const selection = pickRuntime(input.capabilities, input.preferredRuntime, input.preferredModel);
    if (!selection) {
      callbacks.onComplete(input.fallbackReply);
      return;
    }

    const prompt = buildPrompt(input);
    let stdoutBuffer = "";
    let assistantText = "";

    const processHandle = this.spawnRunner(
      selection.command,
      buildArgs(selection, input, prompt),
      {
        cwd: input.cwd,
        env: process.env,
        onStdout: (chunk) => {
          stdoutBuffer += chunk;
          const parsed = drainCodexJson(stdoutBuffer);
          stdoutBuffer = parsed.remainder;
          for (const event of parsed.events) {
            const sessionId = extractSessionId(event);
            if (sessionId) {
              callbacks.onSessionStarted?.(sessionId);
            }
            const nextText = extractAssistantText(event);
            if (!nextText || nextText.length <= assistantText.length) {
              continue;
            }
            const delta = nextText.slice(assistantText.length);
            assistantText = nextText;
            if (delta) {
              callbacks.onDelta(delta);
            }
          }
        },
        onStderr: () => undefined
      }
    );

    void processHandle.wait().then((result) => {
      const parsed = drainCodexJson(stdoutBuffer);
      for (const event of parsed.events) {
        const sessionId = extractSessionId(event);
        if (sessionId) {
          callbacks.onSessionStarted?.(sessionId);
        }
        const nextText = extractAssistantText(event);
        if (nextText && nextText.length > assistantText.length) {
          const delta = nextText.slice(assistantText.length);
          assistantText = nextText;
          if (delta) {
            callbacks.onDelta(delta);
          }
        }
      }

      if (!result.ok) {
        callbacks.onError(result.stderr.trim() || result.stdout.trim() || "Codex chat failed");
        return;
      }

      const finalReply = assistantText.trim() || input.fallbackReply;
      callbacks.onComplete(finalReply);
    });
  }
}

function pickRuntime(
  capabilities: ProviderCapabilitySnapshot[],
  preferredRuntimeOverride?: StrategistRuntimeInput["preferredRuntime"],
  preferredModelOverride?: string | null
): RuntimeSelection | null {
  const configuredRuntime = process.env.STRATEGIST_CHAT_RUNTIME;
  if (configuredRuntime !== undefined && !configuredRuntime.trim()) {
    return null;
  }
  const preferredRuntime =
    preferredRuntimeOverride && (preferredRuntimeOverride === "codex-local" || preferredRuntimeOverride === "opencode")
      ? preferredRuntimeOverride
      : inputPreferredRuntime(capabilities, configuredRuntime);
  const capability = capabilities.find((candidate) => candidate.runtime === preferredRuntime);
  if (!capability || capability.installStatus !== "installed" || capability.authStatus === "logged_out" || !capability.command) {
    return null;
  }
  return {
    runtime: preferredRuntime,
    command: capability.command,
    model:
      preferredModelOverride?.trim() ||
      process.env.STRATEGIST_CHAT_MODEL?.trim() ||
      capability.models[0] ||
      (preferredRuntime === "opencode" ? "openai/gpt-5.4" : "gpt-5.4-mini")
  };
}

function inputPreferredRuntime(
  capabilities: ProviderCapabilitySnapshot[],
  configuredRuntime: string | undefined
): "codex-local" | "opencode" {
  const allowed = new Set(["codex-local", "opencode"]);
  if (configuredRuntime?.trim() && allowed.has(configuredRuntime.trim())) {
    return configuredRuntime.trim() as "codex-local" | "opencode";
  }
  if (capabilities.some((candidate) => candidate.runtime === "opencode")) {
    return "opencode";
  }
  return "codex-local";
}

function buildArgs(selection: RuntimeSelection, input: StrategistRuntimeInput, prompt: string): string[] {
  if (selection.runtime === "opencode") {
    const args = ["run", "--format", "json", "--dir", input.cwd];
    if (input.sessionId) {
      args.push("--session", input.sessionId);
    }
    if (selection.model) {
      args.push("--model", selection.model);
    }
    args.push(prompt);
    return args;
  }
  const args = input.sessionId
    ? ["exec", "resume", input.sessionId, "--skip-git-repo-check", "--json"]
    : ["exec", "--cd", input.cwd, "--sandbox", "read-only", "--skip-git-repo-check", "--json"];
  if (selection.model) {
    args.push("--model", selection.model);
  }
  args.push(prompt);
  return args;
}

function buildPrompt(input: StrategistRuntimeInput): string {
  if (isSmallTalk(input.message)) {
    return [
      "You are the chat-facing assistant inside a coding orchestrator.",
      "Reply naturally and briefly.",
      "Do not mention repo state, internal routing, or delegated work unless the user asks for it.",
      "",
      `User message:\n${input.message}`,
      "",
      "Return only the assistant reply text."
    ].join("\n");
  }

  const recentConversation =
    input.conversation.messages
      .slice(-3)
      .map((message) => `${message.role}: ${truncate(message.content, 220)}`)
      .join("\n") || "none";
  const workspaceSummary = truncate(input.projectSummary?.trim() || "No fresh workspace summary available.", 220);
  const fallbackReply = truncate(input.fallbackReply, 260);

  return [
    "You are the chat-facing assistant inside a coding orchestrator.",
    "Be natural, concise, and direct.",
    "Reply like a normal assistant, not a rules engine or dashboard.",
    "If execution should be delegated, say so naturally without inventing internal ids.",
    "Do not mention confidence percentages, dirty files, active roots, or scoring heuristics unless the user explicitly asks.",
    "",
    `Workspace summary:\n${workspaceSummary}`,
    "",
    `Recent conversation:\n${recentConversation}`,
    "",
    `User message:\n${input.message}`,
    "",
    `Fallback draft reply:\n${fallbackReply}`,
    "",
    "Return only the assistant reply text."
  ].join("\n");
}

function drainCodexJson(raw: string): { events: unknown[]; remainder: string } {
  const events: unknown[] = [];
  let remainder = raw;
  while (true) {
    const newlineIndex = remainder.indexOf("\n");
    if (newlineIndex === -1) {
      break;
    }
    const line = remainder.slice(0, newlineIndex).trim();
    remainder = remainder.slice(newlineIndex + 1);
    if (!line.startsWith("{")) {
      continue;
    }
    try {
      events.push(JSON.parse(line));
    } catch {
      continue;
    }
  }
  return { events, remainder };
}

function extractAssistantText(event: unknown): string | null {
  if (!event || typeof event !== "object") {
    return null;
  }
  const eventType = "type" in event && typeof event.type === "string" ? event.type : "";
  if (eventType === "item.completed" || eventType === "item.updated") {
    const item = "item" in event ? event.item : null;
    if (!item || typeof item !== "object") {
      return null;
    }
    if (!("type" in item) || item.type !== "agent_message") {
      return null;
    }
    return "text" in item && typeof item.text === "string" ? item.text : null;
  }
  if (eventType !== "text") {
    return null;
  }
  const part = "part" in event ? event.part : null;
  if (!part || typeof part !== "object") {
    return null;
  }
  return "text" in part && typeof part.text === "string" ? part.text : null;
}

function extractSessionId(event: unknown): string | null {
  if (!event || typeof event !== "object") {
    return null;
  }
  const eventType = "type" in event && typeof event.type === "string" ? event.type : "";
  if (eventType === "thread.started") {
    return "thread_id" in event && typeof event.thread_id === "string" ? event.thread_id : null;
  }
  return "sessionID" in event && typeof event.sessionID === "string" ? event.sessionID : null;
}

function isSmallTalk(message: string): boolean {
  const normalized = message.trim().toLowerCase();
  return /^(hi|hello|hey|yo|sup|how are you|how r u|wyd|thanks|thank you|ok|okay)\b/.test(normalized);
}

function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 1).trimEnd()}…`;
}
