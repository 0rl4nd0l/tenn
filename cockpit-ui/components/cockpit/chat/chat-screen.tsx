'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { TerminalMessage } from './terminal-message'
import { TerminalInput } from './terminal-input'
import { useCockpitStore, generateId } from '@/lib/cockpit-store'
import { streamChat, sendChatMessage, executeAction, restartBackend } from '@/lib/api-client'
import type { ChatMessage as ChatMessageType, ActionPreview } from '@/lib/cockpit-types'
import { toast } from 'sonner'

export function ChatScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingStatus, setStreamingStatus] = useState('Preparing request')
  const [streamingMetadata, setStreamingMetadata] = useState<Partial<ChatMessageType>>({})
  
  const { activeTicker, sessionId, chatModel, addCost, setLatency, setActiveModel } = useCockpitStore()
  const scrollRef = useRef<HTMLDivElement>(null)

  // Wait for hydration to finish to avoid SSR/CSR mismatch with Zustand
  useEffect(() => {
    setHasHydrated(true)
  }, [])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  const handleSend = async (content: string) => {
    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    setIsStreaming(true)
    setStreamingContent('')
    setStreamingStatus('Preparing request')
    setStreamingMetadata({})

    // Slash command handling
    if (content.startsWith('/')) {
      if (content.trim() === '/restart backend') {
        try {
          const result = await restartBackend()
          const systemMessage: ChatMessageType = {
            id: generateId(),
            role: 'assistant',
            content: result.message || 'Backend restarted successfully.',
            timestamp: new Date(),
            metadata: { source: 'local' },
          }
          setMessages(prev => [...prev, systemMessage])
          toast.success(result.message || 'Backend restarted')
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Unknown error'
          toast.error('Backend restart failed: ' + message)
          setMessages(prev => [...prev, {
            id: generateId(),
            role: 'system',
            content: `Backend restart failed: ${message}`,
            timestamp: new Date(),
          }])
        } finally {
          setIsStreaming(false)
        }
        return
      }

      try {
        const response = await sendChatMessage({
          message: content,
          mode: 'analysis',
          ticker: activeTicker,
          sessionId: sessionId,
          model: chatModel,
        })
        
        const systemMessage: ChatMessageType = {
          id: generateId(),
          role: 'assistant',
          content: response.content.answer,
          timestamp: new Date(),
          metadata: {
            model: response.content.model,
            latencyMs: response.content.latency_ms,
            costUsd: 0,
            source: 'local'
          }
        }
        setMessages(prev => [...prev, systemMessage])
      } catch (err) {
        toast.error('Command failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
      } finally {
        setIsStreaming(false)
      }
      return
    }

    // Normal chat with streaming
    let currentContent = ''
    const currentMetadata: Partial<ChatMessageType> = {
      toolTraces: [],
      sources: []
    }

    try {
      streamChat({
        message: content,
        mode: 'analysis',
        ticker: activeTicker,
        sessionId: sessionId,
        model: chatModel,
        onMessage: (event) => {
          switch (event.type) {
            case 'chunk':
              currentContent += event.data.text
              setStreamingContent(currentContent)
              break
            case 'status':
              if (typeof event.data?.stage === 'string' && event.data.stage.trim().length > 0) {
                setStreamingStatus(event.data.stage)
              }
              break
            case 'tool_trace':
              currentMetadata.toolTraces = [...(currentMetadata.toolTraces || []), {
                tool: event.data.tool,
                durationMs: event.data.duration_ms,
                status: 'success'
              }]
              setStreamingMetadata({ ...currentMetadata })
              break
            case 'sources':
              currentMetadata.sources = event.data.items.map((s: any) => ({
                title: s.title,
                score: s.score
              }))
              setStreamingMetadata({ ...currentMetadata })
              break
            case 'action_preview':
              currentMetadata.actionPreview = {
                id: event.data.id,
                name: event.data.name,
                description: event.data.description,
                args: event.data.args,
                requiresConfirmation: true
              }
              setStreamingMetadata({ ...currentMetadata })
              break
            case 'done':
              const finalText =
                typeof event.data?.text === 'string' && event.data.text.trim().length > 0
                  ? event.data.text
                  : currentContent
              const assistantMessage: ChatMessageType = {
                id: generateId(),
                role: 'assistant',
                content: finalText,
                timestamp: new Date(),
                metadata: {
                  model: event.data.model,
                  latencyMs: event.data.latency_ms,
                  costUsd: event.data.cost_usd || 0,
                  source: event.data.source || 'local'
                },
                sources: currentMetadata.sources,
                toolTraces: currentMetadata.toolTraces,
                actionPreview: currentMetadata.actionPreview
              }
              
              // Update global stats
              if (event.data.cost_usd) addCost(event.data.cost_usd)
              if (event.data.latency_ms) setLatency(event.data.latency_ms)
              if (event.data.model) setActiveModel(event.data.model)
              
              setMessages(prev => [...prev, assistantMessage])
              setStreamingContent('')
              setStreamingStatus('')
              setStreamingMetadata({})
              setIsStreaming(false)
              break
            case 'error':
              // Handle error events from backend
              console.error('[Chat] Streaming error event:', event.data)
              const errorMessage = typeof event.data === 'string' ? event.data : 'Chat failed'
              toast.error('Chat error: ' + errorMessage)
              setMessages(prev => [...prev, {
                id: generateId(),
                role: 'system',
                content: `Error: ${errorMessage}`,
                timestamp: new Date(),
              }])
              setStreamingStatus('')
              setIsStreaming(false)
              break
          }
        },
        onError: (err) => {
          console.error('[Chat] Streaming connection error:', err)
          const errorMsg = err?.data || err?.message || 'Connection lost'
          toast.error('Streaming error: ' + errorMsg)
          setMessages(prev => [...prev, {
            id: generateId(),
            role: 'system',
            content: `Connection error: ${errorMsg}`,
            timestamp: new Date(),
          }])
          setStreamingStatus('')
          setIsStreaming(false)
        },
        onEnd: () => {
          setStreamingStatus('')
          setIsStreaming(false)
        }
      })
    } catch (err) {
      console.error('[Chat] Failed to initiate streaming:', err)
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      toast.error('Failed to start chat: ' + errorMsg)
      setMessages(prev => [...prev, {
        id: generateId(),
        role: 'system',
        content: `Failed to start chat: ${errorMsg}`,
        timestamp: new Date(),
      }])
      setIsStreaming(false)
    }
  }

  const handleConfirmAction = useCallback(async (actionPreview: ActionPreview | undefined) => {
    if (!actionPreview) return
    try {
      const result = await executeAction({
        actionId: actionPreview.id,
        args: actionPreview.args,
        sessionId,
      })
      const resultMessage: ChatMessageType = {
        id: generateId(),
        role: 'assistant',
        content: `Action **${actionPreview.name}** executed successfully.\n\n${result.result}`,
        timestamp: new Date(),
        metadata: { source: 'local' },
      }
      setMessages(prev => [...prev, resultMessage])
      toast.success(`Action "${actionPreview.name}" executed`)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      const errorMessage: ChatMessageType = {
        id: generateId(),
        role: 'system',
        content: `Action "${actionPreview.name}" failed: ${errorMsg}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
      toast.error(`Action failed: ${errorMsg}`)
    }
  }, [sessionId])

  const handleCancelAction = useCallback((actionPreview: ActionPreview | undefined) => {
    if (!actionPreview) return
    const cancelMessage: ChatMessageType = {
      id: generateId(),
      role: 'system',
      content: `Action cancelled: ${actionPreview.name}`,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, cancelMessage])
  }, [])

  const handleClearMessages = useCallback(() => {
    setMessages([])
    setStreamingContent('')
    setStreamingMetadata({})
  }, [])

  if (!hasHydrated) return null

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
          cockpit@financial-ai ~ /chat ({activeTicker})
        </span>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4 pb-4">
          {messages.map((msg) => (
            <TerminalMessage
              key={msg.id}
              message={msg}
              onConfirmAction={handleConfirmAction}
              onCancelAction={handleCancelAction}
            />
          ))}
          {isStreaming && streamingContent && (
            <div className="space-y-2">
              {streamingStatus && (
                <div className="flex items-center gap-2 text-blue-400/70 font-mono text-xs pl-1">
                  <span className="terminal-cursor" />
                  <span>Stage: {streamingStatus}</span>
                </div>
              )}
              <TerminalMessage 
                message={{
                  id: 'streaming',
                  role: 'assistant',
                  content: streamingContent,
                  timestamp: new Date(),
                  ...streamingMetadata
                }} 
                isStreaming={true}
              />
            </div>
          )}
          {isStreaming && !streamingContent && (
            <div className="flex items-center gap-2 text-blue-400/60 font-mono text-sm">
              <span className="terminal-cursor" />
              <span>{streamingStatus || 'Preparing request...'}</span>
            </div>
          )}
        </div>
      </ScrollArea>

      <TerminalInput onSend={handleSend} disabled={isStreaming} onClear={handleClearMessages} />
    </div>
  )
}
