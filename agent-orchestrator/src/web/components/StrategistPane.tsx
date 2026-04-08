import { FormEvent, useState } from "react";
import { StrategistConversation } from "../../shared/types";

interface StrategistPaneProps {
  conversation: StrategistConversation;
  hasDelegatedWork: boolean;
  onSend(message: string): Promise<void>;
}

export function StrategistPane({ conversation, hasDelegatedWork, onSend }: StrategistPaneProps) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suggestions = [
    "How is the system looking?",
    "I want to fix the orchestrator UI flow."
  ];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim()) {
      return;
    }
    setSending(true);
    setError(null);
    try {
      await onSend(message.trim());
      setMessage("");
    } catch (nextError) {
      setError((nextError as Error).message);
    } finally {
      setSending(false);
    }
  };

  const sendSuggestion = async (prompt: string) => {
    setSending(true);
    setError(null);
    try {
      setMessage(prompt);
      await onSend(prompt);
      setMessage("");
    } catch (nextError) {
      setError((nextError as Error).message);
    } finally {
      setSending(false);
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
            disabled={sending}
            onClick={() => {
              void sendSuggestion(suggestion);
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
      <div className="message-stack clean-chat-stack">
        {conversation.messages.slice(-8).map((messageItem) => (
          <article key={messageItem.id} className={`message ${messageItem.role}`}>
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
          placeholder="Ask a question, describe a goal, or tell GPT what you want done."
          rows={5}
        />
        <div className="composer-footer">
          <button type="submit" disabled={sending}>
            {sending ? "Thinking..." : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
