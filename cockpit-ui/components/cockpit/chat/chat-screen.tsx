'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { TerminalMessage } from './terminal-message'
import { TerminalInput } from './terminal-input'
import { generateId } from '@/lib/cockpit-store'
import { sendChatMessage } from '@/lib/api-client'
import type { ChatMessage as ChatMessageType } from '@/lib/cockpit-types'
import { createChatSessionId, loadChatSession, saveChatSession } from '@/lib/chat-session-store'

export function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [activeTicker, setActiveTicker] = useState('BHP')
  const [sessionId, setSessionId] = useState('')
  const [draft, setDraft] = useState('')
  const [isHydrated, setIsHydrated] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  useEffect(() => {
    const stored = loadChatSession()
    setMessages(stored.messages)
    setActiveTicker(stored.activeTicker)
    setSessionId(stored.sessionId)
    setDraft(stored.draft)
    setIsHydrated(true)
  }, [])

  useEffect(() => {
    if (!isHydrated) {
      return
    }
    saveChatSession({
      sessionId: sessionId || createChatSessionId(),
      activeTicker,
      draft,
      messages,
    })
  }, [activeTicker, draft, isHydrated, messages, sessionId])

  const handleSend = async (content: string) => {
    const resolvedSessionId = sessionId || createChatSessionId()
    if (!sessionId) {
      setSessionId(resolvedSessionId)
    }

    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    setIsStreaming(true)
    setStreamingContent('')

    try {
      const response = await sendChatMessage({
        message: content,
        mode: 'analysis',
        ticker: activeTicker,
        sessionId: resolvedSessionId,
      })

      const sources: ChatMessageType['sources'] = response.content.sources?.map(s => ({
        title: s.title,
        score: s.score,
      }))

      const toolTraces: ChatMessageType['toolTraces'] = response.content.tool_traces?.map(t => ({
        tool: t.tool,
        durationMs: t.duration_ms ?? 0,
        status: 'success' as const,
      }))

      const assistantMessage: ChatMessageType = {
        id: generateId(),
        role: 'assistant',
        content: response.content.answer,
        timestamp: new Date(),
        metadata: {
          model: response.content.model,
          latencyMs: response.content.latency_ms,
          costUsd: 0,
          source: 'local',
        },
        sources,
        toolTraces,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const detail = err instanceof Error ? err.message : 'Unknown error'
      const errorMessage: ChatMessageType = {
        id: generateId(),
        role: 'system',
        content: `ERROR: ${detail}. Retry with /reconnect`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsStreaming(false)
      setStreamingContent('')
    }
  }

  return (
    <div className="flex h-full flex-col terminal-container overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border/30 bg-black/20 relative z-10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/80" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
          <div className="w-3 h-3 rounded-full bg-green-500/80" />
        </div>
        <span className="font-mono text-xs terminal-text-dim ml-2">
          cockpit@financial-ai ~ /chat
        </span>
        <div className="ml-auto font-mono text-[10px] terminal-text-dim">
          {messages.length} messages
        </div>
      </div>

      {/* Terminal output area */}
      <ScrollArea className="flex-1 relative z-10" ref={scrollRef}>
        <div className="p-4 font-mono text-sm space-y-1">
          {/* Boot message */}
          <div className="terminal-text-dim text-xs mb-4">
            <div>Financial Cockpit v2.0.0 - Terminal Interface</div>
            <div>Type /help for available commands</div>
            <div className="mt-1">---</div>
          </div>

          {messages.map((message) => (
            <TerminalMessage key={message.id} message={message} />
          ))}
          
          {isStreaming && (
            <TerminalMessage
              message={{
                id: 'streaming',
                role: 'assistant',
                content: 'Thinking...',
                timestamp: new Date(),
              }}
              isStreaming
            />
          )}
        </div>
      </ScrollArea>

      {/* Terminal input */}
      <TerminalInput 
        onSend={handleSend} 
        disabled={isStreaming}
        value={draft}
        onValueChange={setDraft}
      />
    </div>
  )
}
