'use client'

import type { ChatMessage } from './cockpit-types'

const STORAGE_KEY = 'cockpit-chat-session-v1'

interface StoredChatMessage
  extends Omit<ChatMessage, 'timestamp'> {
  timestamp: string
}

export interface PersistedChatSession {
  sessionId: string
  activeTicker: string
  draft: string
  messages: ChatMessage[]
}

function isValidRole(value: unknown): value is ChatMessage['role'] {
  return value === 'user' || value === 'assistant' || value === 'system'
}

function deserializeMessage(value: unknown): ChatMessage | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  const row = value as Record<string, unknown>
  if (typeof row.id !== 'string' || !isValidRole(row.role) || typeof row.content !== 'string') {
    return null
  }

  const timestamp = new Date(typeof row.timestamp === 'string' ? row.timestamp : '')
  if (Number.isNaN(timestamp.getTime())) {
    return null
  }

  return {
    id: row.id,
    role: row.role,
    content: row.content,
    timestamp,
    metadata: row.metadata as ChatMessage['metadata'] | undefined,
    sources: row.sources as ChatMessage['sources'] | undefined,
    toolTraces: row.toolTraces as ChatMessage['toolTraces'] | undefined,
    actionPreview: row.actionPreview as ChatMessage['actionPreview'] | undefined,
  }
}

function serializeMessage(message: ChatMessage): StoredChatMessage {
  return {
    ...message,
    timestamp: message.timestamp.toISOString(),
  }
}

export function createChatSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `chat_${Math.random().toString(36).slice(2, 10)}`
}

export function loadChatSession(): PersistedChatSession {
  const fallback: PersistedChatSession = {
    sessionId: createChatSessionId(),
    activeTicker: '',
    draft: '',
    messages: [],
  }

  if (typeof window === 'undefined') {
    return fallback
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return fallback
    }

    const parsed = JSON.parse(raw) as Record<string, unknown>
    const messages = Array.isArray(parsed.messages)
      ? parsed.messages.map(deserializeMessage).filter((item): item is ChatMessage => item !== null)
      : []

    return {
      sessionId:
        typeof parsed.sessionId === 'string' && parsed.sessionId.trim()
          ? parsed.sessionId
          : fallback.sessionId,
      activeTicker:
        typeof parsed.activeTicker === 'string' && parsed.activeTicker.trim()
          ? parsed.activeTicker
          : fallback.activeTicker,
      draft: typeof parsed.draft === 'string' ? parsed.draft : '',
      messages,
    }
  } catch {
    return fallback
  }
}

export function saveChatSession(session: PersistedChatSession): void {
  if (typeof window === 'undefined') {
    return
  }

  const payload = {
    ...session,
    messages: session.messages.map(serializeMessage),
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}
