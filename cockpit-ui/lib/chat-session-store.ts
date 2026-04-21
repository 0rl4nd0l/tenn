'use client'

import type { ChatMessage } from './cockpit-types'

const STORAGE_KEY = 'cockpit-chat-sessions-v2'
const LEGACY_STORAGE_KEY = 'cockpit-chat-session-v1'

interface StoredChatMessage extends Omit<ChatMessage, 'timestamp'> {
  timestamp: string
}

export interface PersistedChatSession {
  sessionId: string
  activeTicker: string
  draft: string
  messages: ChatMessage[]
  updatedAt: string
  title?: string
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

export function loadAllChatSessions(): PersistedChatSession[] {
  if (typeof window === 'undefined') return []
  
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    let parsed: Record<string, any> = raw ? JSON.parse(raw) : {}

    // Migrate from v1 if v2 is empty
    if (Object.keys(parsed).length === 0) {
      const rawV1 = window.localStorage.getItem(LEGACY_STORAGE_KEY)
      if (rawV1) {
        try {
          const parsedV1 = JSON.parse(rawV1)
          if (parsedV1 && parsedV1.sessionId) {
            const migratedSession: PersistedChatSession = {
              sessionId: parsedV1.sessionId,
              activeTicker: parsedV1.activeTicker || '',
              draft: parsedV1.draft || '',
              updatedAt: new Date().toISOString(),
              messages: Array.isArray(parsedV1.messages) 
                ? (parsedV1.messages as unknown[])
                    .map(deserializeMessage)
                    .filter((m: ChatMessage | null): m is ChatMessage => m !== null)
                : []
            }
            saveChatSession(migratedSession)
            // reload after saving to get the migrated data from storage
            const rawMigrated = window.localStorage.getItem(STORAGE_KEY)
            parsed = rawMigrated ? JSON.parse(rawMigrated) : {}
          }
        } catch (e) {
          console.error('Failed to migrate chat session v1', e)
        }
      }
    }

    return Object.values(parsed).map((session: any) => ({
      sessionId: session.sessionId,
      activeTicker: session.activeTicker || '',
      draft: session.draft || '',
      title: session.title,
      updatedAt: session.updatedAt || new Date(0).toISOString(),
      messages: Array.isArray(session.messages) 
        ? (session.messages as unknown[])
            .map(deserializeMessage)
            .filter((m: ChatMessage | null): m is ChatMessage => m !== null)
        : []
    })).sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
  } catch {
    return []
  }
}

export function loadChatSession(sessionId?: string): PersistedChatSession {
  const fallback: PersistedChatSession = {
    sessionId: sessionId || createChatSessionId(),
    activeTicker: '',
    draft: '',
    messages: [],
    updatedAt: new Date().toISOString()
  }

  if (!sessionId || typeof window === 'undefined') {
    return fallback
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback

    const parsed = JSON.parse(raw) as Record<string, any>
    if (parsed[sessionId]) {
      const session = parsed[sessionId]
      return {
        sessionId: session.sessionId,
        activeTicker: session.activeTicker || '',
        draft: session.draft || '',
        title: session.title,
        updatedAt: session.updatedAt || new Date().toISOString(),
        messages: Array.isArray(session.messages)
          ? (session.messages as unknown[])
              .map(deserializeMessage)
              .filter((item: ChatMessage | null): item is ChatMessage => item !== null)
          : []
      }
    }
  } catch {
    // Return fallback on error
  }
  return fallback
}

export function saveChatSession(session: PersistedChatSession): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : {}

    const payload = {
      ...session,
      updatedAt: new Date().toISOString(),
      messages: session.messages.map(serializeMessage),
    }

    // Auto-generate title from first user message if missing
    if (!payload.title && payload.messages.length > 0) {
      const firstUserMsg = payload.messages.find(m => m.role === 'user')
      if (firstUserMsg) {
        payload.title = firstUserMsg.content.slice(0, 40) + (firstUserMsg.content.length > 40 ? '...' : '')
      }
    }

    parsed[session.sessionId] = payload
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed))
  } catch {
    // Ignore storage errors
  }
}

export function deleteChatSession(sessionId: string): void {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw)
    delete parsed[sessionId]
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed))
  } catch {}
}
