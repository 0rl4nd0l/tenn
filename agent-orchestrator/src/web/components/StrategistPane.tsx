import { FormEvent, KeyboardEvent, useState } from "react";
import { StrategistConversation } from "../../shared/types";

interface LiveChatMessage {
  id: string;
  content: string;
  pending?: boolean;
}

interface StrategistPaneProps {
  conversation: StrategistConversation;
  hasDelegatedWork: boolean;
  chatSending: boolean;
  chatRuntime: "codex-local" | "opencode";
  chatModel: string;
  chatModelOptions: string[];
  onChatRuntimeChange(runtime: "codex-local" | "opencode"): void;
  onChatModelChange(model: string): void;
  pendingUserMessage: LiveChatMessage | null;
  streamingAssistantMessage: LiveChatMessage | null;
  onSend(message: string): Promise<void>;
}

export function StrategistPane({
  conversation,
  hasDelegatedWork,
  chatSending,
  chatRuntime,
  chatModel,
  chatModelOptions,
  onChatRuntimeChange,
  onChatModelChange,
  pendingUserMessage,
  streamingAssistantMessage,
  onSend
}: StrategistPaneProps) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const suggestions = [
    "How is the system looking?",
    "I want to fix the orchestrator UI flow."
  ];
  const conversationMessageIds = new Set(conversation.messages.map((messageItem) => messageItem.id));
  const messages = [...conversation.messages.slice(-8)];
  if (pendingUserMessage && !conversationMessageIds.has(pendingUserMessage.id)) {
    messages.push({
      id: pendingUserMessage.id,
      role: "user" as const,
      content: pendingUserMessage.content,
      createdAt: new Date().toISOString()
    });
  }
  if (streamingAssistantMessage) {
    messages.push({
      id: streamingAssistantMessage.id,
      role: "assistant" as const,
      content: streamingAssistantMessage.content || "Codex is thinking…",
      createdAt: new Date().toISOString()
    });
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim()) {
      return;
    }
    setError(null);
    try {
      await onSend(message.trim());
      setMessage("");
    } catch (nextError) {
      setError((nextError as Error).message);
    }
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    if (!message.trim() || chatSending) {
      return;
    }
    void submit(event as unknown as FormEvent);
  };

  const sendSuggestion = async (prompt: string) => {
    setError(null);
    try {
      setMessage(prompt);
      await onSend(prompt);
      setMessage("");
    } catch (nextError) {
      setError((nextError as Error).message);
    }
  };

  return (
    <section className="panel strategist-panel">
      <div className="strategist-hero">
        <div className="strategist-copy">
          <p className="eyebrow">Main Chat</p>
          <h2>Chat with GPT</h2>
          <p className="strategy-note">
            Clean chat first. Execution panels stay out of the way until the assistant decides to delegate.
          </p>
        </div>
        <div className="strategist-status">
          <span className={`badge ${hasDelegatedWork ? "ok" : "neutral"}`}>
            {hasDelegatedWork ? "work delegated" : "chat only"}
          </span>
        </div>
      </div>
      <div className="prompt-strip" aria-label="Suggested strategist prompts">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="prompt-chip"
            disabled={chatSending}
            onClick={() => {
              void sendSuggestion(suggestion);
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
      <div className="chat-runtime-bar">
        <label className="field compact-field">
          <span>Chat runtime</span>
          <select
            value={chatRuntime}
            disabled={chatSending}
            onChange={(event) => onChatRuntimeChange(event.target.value as "codex-local" | "opencode")}
          >
            <option value="opencode">opencode</option>
            <option value="codex-local">codex-local</option>
          </select>
        </label>
        <label className="field compact-field">
          <span>Provider / model</span>
          <select
            value={chatModel}
            disabled={chatSending || chatModelOptions.length === 0}
            onChange={(event) => onChatModelChange(event.target.value)}
          >
            {chatModelOptions.map((modelOption) => (
              <option key={modelOption} value={modelOption}>
                {modelOption}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="message-stack clean-chat-stack">
        {messages.map((messageItem) => (
          <article
            key={messageItem.id}
            className={`message ${messageItem.role} ${
              streamingAssistantMessage?.id === messageItem.id && streamingAssistantMessage.pending ? "streaming" : ""
            }`}
          >
            <span>{messageItem.role === "assistant" ? "GPT" : messageItem.role}</span>
            <p>{messageItem.content}</p>
          </article>
        ))}
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <form className="composer" onSubmit={submit}>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Ask a question, describe a goal, or tell GPT what you want done."
          rows={5}
        />
        <div className="composer-footer">
          <button type="submit" disabled={chatSending}>
            {chatSending ? "Codex is working..." : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
