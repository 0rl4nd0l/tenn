'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { TerminalMessage } from './terminal-message'
import { TerminalInput } from './terminal-input'
import { useCockpitStore, generateId } from '@/lib/cockpit-store'
import { streamChat, sendChatMessage, executeAction, restartBackend } from '@/lib/api-client'
import type { ChatMessage as ChatMessageType, ActionPreview } from '@/lib/cockpit-types'
import { toast } from 'sonner'

type FlagState = 'saving' | 'saved'

type FlagFeedbackResponse = {
  report_id: string
  report_dir: string
  codex_prompt: string
  analysis_summary?: string | null
}

async function copyFlagPromptToClipboard(prompt: string): Promise<boolean> {
  const text = prompt.trim()
  if (!text) {
    return false
  }
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

const FLAG_NOTE_PRESETS = [
  'Hallucination',
  'Wrong ticker context',
  'Bad calculation',
  'Unsupported claim',
  'Missed cited evidence',
] as const

function serializeMessageForFeedback(message: ChatMessageType) {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    timestamp: message.timestamp.toISOString(),
    metadata: message.metadata,
    thinking: message.thinking,
    sources: message.sources,
    toolTraces: message.toolTraces,
    actionPreview: message.actionPreview,
    chart: message.chart ? { title: message.chart.title } : undefined,
  }
}

export function ChatScreen() {
  const [hasHydrated, setHasHydrated] = useState(false)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingStatus, setStreamingStatus] = useState('Connecting to backend stream...')
  const [streamingStatusStartedAt, setStreamingStatusStartedAt] = useState<number | null>(null)
  const [streamingClockMs, setStreamingClockMs] = useState<number>(Date.now())
  const [streamingMetadata, setStreamingMetadata] = useState<Partial<ChatMessageType>>({})
  const [flagStates, setFlagStates] = useState<Record<string, FlagState>>({})
  const [pendingFlagMessage, setPendingFlagMessage] = useState<ChatMessageType | null>(null)
  const [flagNote, setFlagNote] = useState('')
  const activeStreamRef = useRef<{ close: () => void } | null>(null)
  const statusFallbackTimersRef = useRef<number[]>([])
  const receivedServerStatusRef = useRef(false)
  const actionInFlightRef = useRef(false)
  
  const {
    activeTicker,
    sessionId,
    chatModel,
    sessionStats,
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

  const setStreamingStage = useCallback((nextStage: string) => {
    setStreamingStatus((prev) => {
      if (prev !== nextStage) {
        setStreamingStatusStartedAt(Date.now())
      }
      return nextStage
    })
  }, [])

  const clearStreamingStage = useCallback(() => {
    setStreamingStatus('')
    setStreamingStatusStartedAt(null)
  }, [])

  useEffect(() => {
    if (!isStreaming || !streamingStatusStartedAt) {
      return
    }
    const intervalId = window.setInterval(() => {
      setStreamingClockMs(Date.now())
    }, 250)
    return () => window.clearInterval(intervalId)
  }, [isStreaming, streamingStatusStartedAt])

  const renderStreamingStatus = useCallback((fallback: string) => {
    const label = (streamingStatus || fallback).trim()
    if (!label) {
      return fallback
    }
    if (!isStreaming || !streamingStatusStartedAt) {
      return label
    }
    const elapsedMs = Math.max(0, streamingClockMs - streamingStatusStartedAt)
    return `${label} (${(elapsedMs / 1000).toFixed(1)}s)`
  }, [isStreaming, streamingClockMs, streamingStatus, streamingStatusStartedAt])

  const formatStageLabel = useCallback((rawStage: string): string => {
    const stage = rawStage.trim()
    if (!stage) return 'Working...'
    if (stage.startsWith('Switching model:')) return stage
    if (stage.startsWith('Model alias resolved:')) return stage
    if (stage.startsWith('Model ready:')) return stage
    if (stage.startsWith('Using selected model:')) return stage.replace('Using selected model:', 'Using model:')
    if (stage.startsWith('Using active model:')) return stage.replace('Using active model:', 'Using model:')
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
    const requestedModel = String(chatModel || '').trim()
    const activeModel = String(sessionStats.activeModel || '').trim()
    const hasModelSwitch = requestedModel.length > 0 && activeModel.length > 0 && requestedModel !== activeModel

    setStreamingStage(
      hasModelSwitch
        ? `Switching model: ${activeModel} -> ${requestedModel}`
        : 'Connecting to backend stream...'
    )
    setStreamingMetadata({})

    statusFallbackTimersRef.current = [
      window.setTimeout(() => {
        if (!receivedServerStatusRef.current) {
          setStreamingStage('Waiting for backend status update...')
        }
      }, 900),
      window.setTimeout(() => {
        if (!receivedServerStatusRef.current) {
          if (hasModelSwitch) {
            setStreamingStage(`Waiting for model switch: ${activeModel} -> ${requestedModel}`)
          } else {
            setStreamingStage('Waiting for model response...')
          }
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
          },
          chart: response.content.chart,
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
    let streamFinalized = false
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
                setStreamingStage(formatStageLabel(event.data.stage))
              }
              break
            case 'thinking':
              currentMetadata.thinking = {
                assessment: event.data.assessment || '',
                plan: event.data.plan || '',
              }
              setStreamingMetadata({ ...currentMetadata })
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
            case 'chart':
              if (event.data && typeof event.data === 'object') {
                currentMetadata.chart = event.data as ChatMessageType['chart']
                setStreamingMetadata({ ...currentMetadata })
              }
              break
            case 'done':
              streamFinalized = true
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
                thinking: currentMetadata.thinking,
                sources: currentMetadata.sources,
                toolTraces: currentMetadata.toolTraces,
                actionPreview: currentMetadata.actionPreview,
                chart: (event.data?.chart as ChatMessageType['chart']) || currentMetadata.chart,
              }
              
              // Update global stats
              if (event.data.cost_usd) addCost(event.data.cost_usd)
              if (event.data.latency_ms) setLatency(event.data.latency_ms)
              if (event.data.model) setActiveModel(event.data.model)
              
              setMessages(prev => [...prev, assistantMessage])
              setStreamingContent('')
              clearStreamingStage()
              setStreamingMetadata({})
              setIsStreaming(false)
              setChatCompletionActive(false)
              clearStatusFallbackTimers()
              activeStreamRef.current = null
              break
            case 'error':
              streamFinalized = true
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
              clearStreamingStage()
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
          clearStreamingStage()
          setIsStreaming(false)
          setChatCompletionActive(false)
          clearStatusFallbackTimers()
          activeStreamRef.current = null
        },
        onEnd: () => {
          if (!streamFinalized) {
            const fallbackText = currentContent.trim()
            if (fallbackText || currentMetadata.actionPreview) {
              setMessages(prev => [...prev, {
                id: generateId(),
                role: 'assistant',
                content: fallbackText || 'Response ended before a final message was emitted.',
                timestamp: new Date(),
                metadata: { source: 'local' },
                thinking: currentMetadata.thinking,
                sources: currentMetadata.sources,
                toolTraces: currentMetadata.toolTraces,
                actionPreview: currentMetadata.actionPreview,
              }])
            } else {
              setMessages(prev => [...prev, {
                id: generateId(),
                role: 'system',
                content: 'Chat stream ended before a final response was received.',
                timestamp: new Date(),
              }])
            }
          }
          clearStreamingStage()
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
      clearStreamingStage()
      setStreamingMetadata({})
      clearStatusFallbackTimers()
      
      toast.info('Chat cancelled')
    }
  }, [clearStatusFallbackTimers, clearStreamingStage, setChatCompletionActive])

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
        chart: result.chart,
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
    setFlagStates({})
    setPendingFlagMessage(null)
    setFlagNote('')
  }, [])

  const submitFlagMessage = useCallback(async (message: ChatMessageType, note: string) => {
    if (message.role !== 'assistant') {
      return
    }
    if (flagStates[message.id]) {
      return
    }

    setFlagStates((prev) => ({ ...prev, [message.id]: 'saving' }))
    try {
      const response = await fetch('/api/cockpit/feedback/flag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          ticker: activeTicker,
          note: note.trim() || undefined,
          flagged_message: serializeMessageForFeedback(message),
          transcript: messages.map(serializeMessageForFeedback),
          frontend_context: {
            source: 'cockpit-ui-chat',
            activeTicker,
            sessionId,
            chatModel,
            preferences,
            clientTimestamp: new Date().toISOString(),
          },
        }),
      })

      const payload = (await response.json().catch(() => null)) as FlagFeedbackResponse | { detail?: string } | null
      if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
          ? String(payload.detail || '')
          : ''
        throw new Error(detail || `HTTP ${response.status}`)
      }

      setFlagStates((prev) => ({ ...prev, [message.id]: 'saved' }))
      setPendingFlagMessage(null)
      setFlagNote('')
      const result = payload as FlagFeedbackResponse
      const copiedPrompt = await copyFlagPromptToClipboard(result.codex_prompt)
      toast.success(result.analysis_summary?.trim()
        ? copiedPrompt
          ? `Flag saved and Codex prompt copied: ${result.analysis_summary}`
          : `Flag saved: ${result.analysis_summary}`
        : copiedPrompt
          ? `Flag saved and Codex prompt copied: ${result.report_dir}`
          : `Flag saved to ${result.report_dir}`)
    } catch (error) {
      setFlagStates((prev) => {
        const next = { ...prev }
        delete next[message.id]
        return next
      })
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to flag response: ${errorMessage}`)
    }
  }, [activeTicker, chatModel, flagStates, messages, preferences, sessionId])

  const handleFlagMessage = useCallback((message: ChatMessageType) => {
    if (message.role !== 'assistant' || flagStates[message.id]) {
      return
    }
    setPendingFlagMessage(message)
    setFlagNote('')
  }, [flagStates])

  const pendingFlagState = pendingFlagMessage ? flagStates[pendingFlagMessage.id] : undefined
  const isPendingFlagSaving = pendingFlagState === 'saving'

  const closeFlagDialog = useCallback(() => {
    if (isPendingFlagSaving) {
      return
    }
    setPendingFlagMessage(null)
    setFlagNote('')
  }, [isPendingFlagSaving])

  const handleFlagSubmit = useCallback(async () => {
    if (!pendingFlagMessage) {
      return
    }
    await submitFlagMessage(pendingFlagMessage, flagNote)
  }, [flagNote, pendingFlagMessage, submitFlagMessage])

  if (!hasHydrated) return null

  return (
    <div className="flex h-full flex-col terminal-container overflow-hidden">
      <Dialog open={Boolean(pendingFlagMessage)} onOpenChange={(open) => {
        if (!open) {
          closeFlagDialog()
        }
      }}>
        <DialogContent className="border-red-500/30 bg-zinc-950 text-zinc-100 sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-mono text-sm text-red-300">Flag response</DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Add a short optional note so the saved report explains what was wrong.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {FLAG_NOTE_PRESETS.map((preset) => {
                const selected = flagNote === preset
                return (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setFlagNote(preset)}
                    disabled={isPendingFlagSaving}
                    className={selected
                      ? 'rounded border border-red-400/60 bg-red-500/20 px-2 py-1 font-mono text-[11px] text-red-100 transition-colors disabled:cursor-default disabled:opacity-60'
                      : 'rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px] text-zinc-300 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60'}
                  >
                    {preset}
                  </button>
                )
              })}
            </div>
            <Textarea
              value={flagNote}
              onChange={(event) => setFlagNote(event.target.value.slice(0, 280))}
              placeholder="Optional note, e.g. wrong ticker context, unsupported claim, bad math"
              disabled={isPendingFlagSaving}
              maxLength={280}
              rows={4}
              className="border-red-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500"
            />
            <div className="text-right font-mono text-[11px] text-zinc-500">
              {flagNote.length}/280
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={closeFlagDialog}
              disabled={isPendingFlagSaving}
              className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-200 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleFlagSubmit()}
              disabled={isPendingFlagSaving}
              className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 font-mono text-xs text-red-200 transition-colors hover:bg-red-500/20 disabled:cursor-default disabled:opacity-60"
            >
              {isPendingFlagSaving ? 'Saving...' : 'Save flag'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
            <div key={msg.id} className="space-y-1">
              <TerminalMessage
                message={msg}
                onConfirmAction={handleConfirmAction}
                onCancelAction={handleCancelAction}
              />
              {msg.role === 'assistant' && (
                <div className="ml-6 flex items-center">
                  <button
                    type="button"
                    onClick={() => handleFlagMessage(msg)}
                    disabled={Boolean(flagStates[msg.id])}
                    className="rounded border border-red-500/30 bg-red-500/8 px-2 py-0.5 font-mono text-[11px] text-red-300 transition-colors hover:bg-red-500/15 disabled:cursor-default disabled:opacity-70"
                  >
                    {flagStates[msg.id] === 'saving'
                      ? '[flagging...]'
                      : flagStates[msg.id] === 'saved'
                        ? '[flagged]'
                        : '[flag response]'}
                  </button>
                </div>
              )}
            </div>
          ))}
          {isStreaming && streamingContent && (
            <div className="space-y-2">
              {streamingStatus && (
                <div className="flex items-center gap-2 text-blue-400/70 font-mono text-xs pl-1">
                  <span className="terminal-cursor" />
                  <span>Stage: {renderStreamingStatus('Preparing request...')}</span>
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
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-blue-400/60 font-mono text-sm">
                <span className="terminal-cursor" />
                <span>{renderStreamingStatus('Preparing request...')}</span>
              </div>
              {streamingMetadata.thinking && (streamingMetadata.thinking.assessment || streamingMetadata.thinking.plan) && (
                <div className="ml-4 pl-3 border-l border-purple-500/20 text-sm text-purple-400/60 space-y-1">
                  {streamingMetadata.thinking.assessment && (
                    <div>
                      <span className="text-purple-400/80 font-semibold">Assessment: </span>
                      <span className="whitespace-pre-wrap">{streamingMetadata.thinking.assessment}</span>
                    </div>
                  )}
                  {streamingMetadata.thinking.plan && (
                    <div>
                      <span className="text-purple-400/80 font-semibold">Plan: </span>
                      <span className="whitespace-pre-wrap">{streamingMetadata.thinking.plan}</span>
                    </div>
                  )}
                </div>
              )}
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
