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
  const [streamingStatus, setStreamingStatus] = useState('Connecting to backend stream...')
  const [streamingMetadata, setStreamingMetadata] = useState<Partial<ChatMessageType>>({})
  const activeStreamRef = useRef<{ close: () => void } | null>(null)
  const statusFallbackTimersRef = useRef<number[]>([])
  const receivedServerStatusRef = useRef(false)
  const actionInFlightRef = useRef(false)
  
  const {
    activeTicker,
    sessionId,
    chatModel,
    preferences,
    addCost,
    setLatency,
    setActiveModel,
    setChatCompletionActive,
  } = useCockpitStore()
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

  useEffect(() => {
    return () => {
      if (activeStreamRef.current) {
        activeStreamRef.current.close()
        activeStreamRef.current = null
      }
      setChatCompletionActive(false)
      if (statusFallbackTimersRef.current.length > 0) {
        statusFallbackTimersRef.current.forEach((timerId) => window.clearTimeout(timerId))
        statusFallbackTimersRef.current = []
      }
    }
  }, [setChatCompletionActive])

  const clearStatusFallbackTimers = useCallback(() => {
    if (statusFallbackTimersRef.current.length > 0) {
      statusFallbackTimersRef.current.forEach((timerId) => window.clearTimeout(timerId))
      statusFallbackTimersRef.current = []
    }
  }, [])

  const formatStageLabel = useCallback((rawStage: string): string => {
    const stage = rawStage.trim()
    if (!stage) return 'Working...'
    if (stage === 'Request accepted') return 'Connected. Preparing tools and request...'
    if (stage === 'Resolving request context') return 'Preparing tools and retrieval context...'
    if (stage === 'Assessing information and planning approach...') return 'Assessing what data is available...'
    if (stage.startsWith('Planning:')) return `Reasoning: ${stage.replace('Planning: ', '')}`
    if (stage.startsWith('LLM reasoning pass')) return `Sending to model: ${stage}`
    if (stage.startsWith('Executing tool:')) return `Preparing tool call: ${stage.replace('Executing tool: ', '')}`
    if (stage === 'Tool execution complete; synthesizing final answer') {
      return 'Tool outputs ready. Composing final response...'
    }
    if (stage === 'Rendering final answer') return 'Rendering final answer...'
    return stage
  }, [])

  const handleSend = async (content: string) => {
    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    clearStatusFallbackTimers()
    receivedServerStatusRef.current = false
    setIsStreaming(true)
    setChatCompletionActive(true)
    setStreamingContent('')
    setStreamingStatus('Connecting to backend stream...')
    setStreamingMetadata({})

    statusFallbackTimersRef.current = [
      window.setTimeout(() => {
        if (!receivedServerStatusRef.current) {
          setStreamingStatus('Preparing tools and request context...')
        }
      }, 900),
      window.setTimeout(() => {
        if (!receivedServerStatusRef.current) {
          setStreamingStatus('Sending prompt to model...')
        }
      }, 2200),
    ]

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
          setChatCompletionActive(false)
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
          webSearch: preferences.webSearchEnabled,
          rag: preferences.ragEnabled,
          dbDiagnostics: preferences.dbDiagnosticsEnabled,
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
        setChatCompletionActive(false)
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
      const source = await streamChat({
        message: content,
        mode: 'analysis',
        ticker: activeTicker,
        sessionId: sessionId,
        model: chatModel,
        webSearch: preferences.webSearchEnabled,
        rag: preferences.ragEnabled,
        dbDiagnostics: preferences.dbDiagnosticsEnabled,
        onMessage: (event) => {
          switch (event.type) {
            case 'chunk':
              currentContent += event.data.text
              setStreamingContent(currentContent)
              break
            case 'status':
              if (typeof event.data?.stage === 'string' && event.data.stage.trim().length > 0) {
                receivedServerStatusRef.current = true
                clearStatusFallbackTimers()
                setStreamingStatus(formatStageLabel(event.data.stage))
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
              {
                const data = event.data || {}
                const normalizedArgs =
                  typeof data.args === 'object' && data.args !== null
                    ? data.args
                    : (typeof data.arguments === 'object' && data.arguments !== null ? data.arguments : {})
                const normalizedId =
                  String(data.id || data.action_id || data.actionId || '').trim()
                const normalizedName =
                  String(data.name || data.action_label || normalizedId || 'Requested action').trim()
                const normalizedDescription =
                  String(data.description || data.explanation || data.impact || '').trim()

              currentMetadata.actionPreview = {
                id: normalizedId,
                name: normalizedName,
                description: normalizedDescription,
                args: normalizedArgs,
                requiresConfirmation: Boolean(
                  data.requiresConfirmation ?? data.requires_confirmation ?? true
                )
              }
              setStreamingMetadata({ ...currentMetadata })
              }
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
              setChatCompletionActive(false)
              clearStatusFallbackTimers()
              activeStreamRef.current = null
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
              setChatCompletionActive(false)
              clearStatusFallbackTimers()
              activeStreamRef.current = null
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
          setChatCompletionActive(false)
          clearStatusFallbackTimers()
          activeStreamRef.current = null
        },
        onEnd: () => {
          setStreamingStatus('')
          setIsStreaming(false)
          setChatCompletionActive(false)
          clearStatusFallbackTimers()
          activeStreamRef.current = null
        }
      })
      
      // Store the stream source so we can cancel it
      activeStreamRef.current = source
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
      setChatCompletionActive(false)
      clearStatusFallbackTimers()
      activeStreamRef.current = null
    }
  }

  const handleCancelStream = useCallback(() => {
    if (activeStreamRef.current) {
      console.log('[Chat] Cancelling active stream')
      activeStreamRef.current.close()
      activeStreamRef.current = null
      
      setMessages(prev => [...prev, {
        id: generateId(),
        role: 'system',
        content: 'Chat cancelled by user',
        timestamp: new Date(),
      }])
      
      setIsStreaming(false)
      setChatCompletionActive(false)
      setStreamingContent('')
      setStreamingStatus('')
      setStreamingMetadata({})
      clearStatusFallbackTimers()
      
      toast.info('Chat cancelled')
    }
  }, [clearStatusFallbackTimers, setChatCompletionActive])

  const handleConfirmAction = useCallback(async (actionPreview: ActionPreview | undefined) => {
    if (!actionPreview) return
    if (actionInFlightRef.current) {
      toast.info('Action already running, please wait...')
      return
    }

    const actionId = String(actionPreview.id || '').trim()
    if (!actionId) {
      const msg = 'Cannot execute action: missing action id in preview payload'
      setMessages(prev => [...prev, {
        id: generateId(),
        role: 'system',
        content: msg,
        timestamp: new Date(),
      }])
      toast.error(msg)
      return
    }

    actionInFlightRef.current = true
    try {
      const result = await executeAction({
        actionId,
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
    } finally {
      actionInFlightRef.current = false
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
        {isStreaming && (
          <button
            type="button"
            onClick={handleCancelStream}
            className="ml-auto rounded border border-red-500/40 bg-red-500/10 px-2 py-1 font-mono text-[11px] text-red-300 transition-colors hover:bg-red-500/20"
          >
            Cancel
          </button>
        )}
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

      <TerminalInput
        onSend={handleSend}
        disabled={isStreaming}
        onClear={handleClearMessages}
      />
    </div>
  )
}
