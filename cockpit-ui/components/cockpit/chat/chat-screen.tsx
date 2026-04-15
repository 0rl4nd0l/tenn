'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
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
import { modelsLikelyMatch, parseCockpitConfig, resolveRuntimeModel } from '@/lib/cockpit-config'
import { useCockpitStore, generateId } from '@/lib/cockpit-store'
import { streamChat, sendChatMessage, executeAction, restartBackend } from '@/lib/api-client'
import type { ChatMessage as ChatMessageType, ActionPreview } from '@/lib/cockpit-types'
import { toast } from 'sonner'

type FeedbackKind = 'good' | 'poor'

type FeedbackState = 'saving-good' | 'saved-good' | 'saving-poor' | 'saved-poor'

type FeedbackCaptureResponse = {
  report_id: string
  feedback_type: FeedbackKind
  report_dir: string
  codex_prompt?: string | null
  analysis_summary?: string | null
}

type PendingFeedback = {
  kind: FeedbackKind
  message: ChatMessageType
}

const BACKEND_PREFIX_RE = /^\s*\/(advisor|cloud|local|ops)\b/i
const ACTION_CONFIRM_INPUTS = new Set([
  '/confirm',
  'confirm',
  'yes',
  'y',
  'yeah',
  'yep',
  'sure',
  'ok',
  'okay',
  'go ahead',
  'proceed',
])
const ACTION_CANCEL_INPUTS = new Set([
  '/cancel',
  'cancel',
  'no',
  'n',
  'nope',
  'skip',
  'stop',
])

function applyApiDefaultOverride(message: string, enabled: boolean): string {
  const trimmed = message.trim()
  if (!enabled || !trimmed) {
    return message
  }
  if (trimmed.startsWith('/') && !BACKEND_PREFIX_RE.test(trimmed)) {
    return message
  }
  return `/cloud ${trimmed}`
}

function resolvePendingActionIntent(message: string): 'confirm' | 'cancel' | null {
  const normalized = message.trim().toLowerCase()
  if (!normalized) return null
  if (ACTION_CONFIRM_INPUTS.has(normalized)) return 'confirm'
  if (ACTION_CANCEL_INPUTS.has(normalized)) return 'cancel'
  return null
}

function sanitizeActionMessage(content: string, actionPreview?: ActionPreview): string {
  if (!actionPreview) {
    return content
  }

  const lines = content
    .split('\n')
    .map((line) => line.trimEnd())
    .filter((line) => !line.trimStart().startsWith('Command:'))
    .map((line) =>
      line.replace(
        /Use \/confirm to execute or \/cancel to skip\./g,
        'Confirm below or type yes/no.'
      )
    )
    .map((line) =>
      line.replace(
        /^Action candidate detected:\s*.+?\.\s*$/i,
        `Action ready: ${actionPreview.name}.`
      )
    )

  return lines.join('\n').trim()
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

const FEEDBACK_NOTE_PRESETS: Record<FeedbackKind, readonly string[]> = {
  good: [
    'Well grounded',
    'Correct ticker context',
    'Good reasoning',
    'Useful synthesis',
    'Strong evidence use',
  ],
  poor: [
    'Hallucination',
    'Wrong ticker context',
    'Bad calculation',
    'Unsupported claim',
    'Missed cited evidence',
  ],
}

function buildFeedbackState(kind: FeedbackKind, status: 'saving' | 'saved'): FeedbackState {
  return `${status}-${kind}` as FeedbackState
}

function isSavingFeedbackState(state: FeedbackState | undefined): boolean {
  return state === 'saving-good' || state === 'saving-poor'
}

function getFeedbackButtonLabel(kind: FeedbackKind, state: FeedbackState | undefined): string {
  if (kind === 'good') {
    if (state === 'saving-good') return '[saving good...]'
    if (state === 'saved-good') return '[saved good]'
    if (state === 'saving-poor') return '[rating poor...]'
    if (state === 'saved-poor') return '[rated poor]'
    return '[good response]'
  }

  if (state === 'saving-poor') return '[flagging...]'
  if (state === 'saved-poor') return '[flagged]'
  if (state === 'saving-good') return '[saving good...]'
  if (state === 'saved-good') return '[rated good]'
  return '[flag response]'
}

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
  const [feedbackStates, setFeedbackStates] = useState<Record<string, FeedbackState>>({})
  const [pendingFeedback, setPendingFeedback] = useState<PendingFeedback | null>(null)
  const [feedbackNote, setFeedbackNote] = useState('')
  const [pendingActionPreview, setPendingActionPreview] = useState<ActionPreview | null>(null)
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
    apiDefaultEnabled,
    addCost,
    setLatency,
    setActiveModel,
    setActiveSource,
    setChatCompletionActive,
    setActiveTicker,
  } = useCockpitStore()
  const { data: configData } = useQuery({
    queryKey: ['cockpit-config-status'],
    queryFn: async () => {
      const response = await fetch('/api/cockpit/config', { cache: 'no-store' })
      if (!response.ok) {
        throw new Error(`Config unavailable (${response.status})`)
      }
      return (await response.json()) as Record<string, unknown>
    },
    refetchInterval: 30000,
    retry: 1,
  })
  const config = parseCockpitConfig(configData)
  const [tickerDraft, setTickerDraft] = useState('')
  const [showTickerInput, setShowTickerInput] = useState(false)
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
    const pendingActionIntent = pendingActionPreview
      ? resolvePendingActionIntent(content)
      : null
    const userMessage: ChatMessageType = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    if (pendingActionPreview && pendingActionIntent === 'confirm') {
      await handleConfirmAction(pendingActionPreview)
      return
    }
    if (pendingActionPreview && pendingActionIntent === 'cancel') {
      handleCancelAction(pendingActionPreview)
      return
    }

    setPendingActionPreview(null)

    clearStatusFallbackTimers()
    receivedServerStatusRef.current = false
    setIsStreaming(true)
    setChatCompletionActive(true)
    setStreamingContent('')
    const requestedModel = String(chatModel || '').trim()
    const activeModel = resolveRuntimeModel(sessionStats.activeModel, config.model)
    const hasModelSwitch = (
      requestedModel.length > 0
      && activeModel.length > 0
      && !modelsLikelyMatch(requestedModel, activeModel)
    )

    setStreamingStage(
      hasModelSwitch
        ? `Switching model: ${activeModel} -> ${requestedModel}`
        : 'Connecting to backend stream...'
    )
    setStreamingMetadata({})
    const outboundMessage = applyApiDefaultOverride(content, apiDefaultEnabled)

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
          message: outboundMessage,
          mode: 'analysis',
          ticker: activeTicker || undefined,
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
            costUsd: response.content.cost_usd || 0,
            source: response.content.source || 'local'
          },
          chart: response.content.chart,
        }
        if (response.content.cost_usd) addCost(response.content.cost_usd)
        if (response.content.latency_ms) setLatency(response.content.latency_ms)
        if (response.content.model) setActiveModel(response.content.model)
        setActiveSource(response.content.source || 'local')
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
        message: outboundMessage,
        mode: 'analysis',
        ticker: activeTicker || undefined,
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
                url: s.url,
                score: s.score,
                snippet: s.snippet,
                publishedAt: s.published_at,
                documentId: s.document_id,
                sourceId: s.source_id,
                docType: s.doc_type,
                path: s.path,
                kind: s.kind,
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
              const normalizedActionPreview = currentMetadata.actionPreview
              const sanitizedFinalText = sanitizeActionMessage(
                finalText,
                normalizedActionPreview,
              )
              const assistantMessage: ChatMessageType = {
                id: generateId(),
                role: 'assistant',
                content: sanitizedFinalText,
                timestamp: new Date(),
                metadata: {
                  model: event.data.model,
                  latencyMs: event.data.latency_ms,
                  costUsd: event.data.cost_usd || 0,
                  source: event.data.source || 'local'
                },
                thinking: currentMetadata.thinking,
                sources: currentMetadata.sources,
                toolTraces: normalizedActionPreview ? [] : currentMetadata.toolTraces,
                actionPreview: normalizedActionPreview,
                chart: (event.data?.chart as ChatMessageType['chart']) || currentMetadata.chart,
              }
              
              // Update global stats
              if (event.data.cost_usd) addCost(event.data.cost_usd)
              if (event.data.latency_ms) setLatency(event.data.latency_ms)
              if (event.data.model) setActiveModel(event.data.model)
              setActiveSource(event.data.source || 'local')
              setPendingActionPreview(normalizedActionPreview ?? null)

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
              const normalizedActionPreview = currentMetadata.actionPreview
              setMessages(prev => [...prev, {
                id: generateId(),
                role: 'assistant',
                content: sanitizeActionMessage(
                  fallbackText || 'Response ended before a final message was emitted.',
                  normalizedActionPreview,
                ),
                timestamp: new Date(),
                metadata: { source: 'local' },
                thinking: currentMetadata.thinking,
                sources: currentMetadata.sources,
                toolTraces: normalizedActionPreview ? [] : currentMetadata.toolTraces,
                actionPreview: normalizedActionPreview,
              }])
              setPendingActionPreview(normalizedActionPreview ?? null)
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
    setPendingActionPreview(null)
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
    setPendingActionPreview(null)
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
    setFeedbackStates({})
    setPendingFeedback(null)
    setFeedbackNote('')
  }, [])

  const submitFeedbackMessage = useCallback(async (message: ChatMessageType, note: string, feedbackType: FeedbackKind) => {
    if (message.role !== 'assistant') {
      return
    }
    if (feedbackStates[message.id]) {
      return
    }

    setFeedbackStates((prev) => ({ ...prev, [message.id]: buildFeedbackState(feedbackType, 'saving') }))
    try {
      const response = await fetch('/api/cockpit/feedback/flag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          ticker: activeTicker,
          feedback_type: feedbackType,
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

      const payload = (await response.json().catch(() => null)) as FeedbackCaptureResponse | { detail?: string } | null
      if (!response.ok) {
        const detail = payload && typeof payload === 'object' && 'detail' in payload
          ? String(payload.detail || '')
          : ''
        throw new Error(detail || `HTTP ${response.status}`)
      }

      setFeedbackStates((prev) => ({ ...prev, [message.id]: buildFeedbackState(feedbackType, 'saved') }))
      setPendingFeedback(null)
      setFeedbackNote('')
      const result = payload as FeedbackCaptureResponse

      if (feedbackType === 'good') {
        toast.success(result.analysis_summary?.trim()
          ? `Good response saved: ${result.analysis_summary}`
          : `Good response saved to ${result.report_dir}`)
      } else {
        const copiedPrompt = result.codex_prompt?.trim()
          ? await copyFlagPromptToClipboard(result.codex_prompt)
          : false
        toast.success(result.analysis_summary?.trim()
          ? copiedPrompt
            ? `Flag saved and Codex prompt copied: ${result.analysis_summary}`
            : `Flag saved: ${result.analysis_summary}`
          : copiedPrompt
            ? `Flag saved and Codex prompt copied: ${result.report_dir}`
            : `Flag saved to ${result.report_dir}`)
      }
    } catch (error) {
      setFeedbackStates((prev) => {
        const next = { ...prev }
        delete next[message.id]
        return next
      })
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      toast.error(`Failed to save feedback: ${errorMessage}`)
    }
  }, [activeTicker, chatModel, feedbackStates, messages, preferences, sessionId])

  const handleFeedbackMessage = useCallback((message: ChatMessageType, kind: FeedbackKind) => {
    if (message.role !== 'assistant' || feedbackStates[message.id]) {
      return
    }
    setPendingFeedback({ message, kind })
    setFeedbackNote('')
  }, [feedbackStates])

  const pendingFeedbackState = pendingFeedback ? feedbackStates[pendingFeedback.message.id] : undefined
  const isPendingFeedbackSaving = isSavingFeedbackState(pendingFeedbackState)
  const pendingFeedbackKind = pendingFeedback?.kind ?? 'poor'
  const isPendingGoodFeedback = pendingFeedbackKind === 'good'
  const pendingFeedbackPresets = FEEDBACK_NOTE_PRESETS[pendingFeedbackKind]

  const closeFeedbackDialog = useCallback(() => {
    if (isPendingFeedbackSaving) {
      return
    }
    setPendingFeedback(null)
    setFeedbackNote('')
  }, [isPendingFeedbackSaving])

  const handleFeedbackSubmit = useCallback(async () => {
    if (!pendingFeedback) {
      return
    }
    await submitFeedbackMessage(pendingFeedback.message, feedbackNote, pendingFeedback.kind)
  }, [feedbackNote, pendingFeedback, submitFeedbackMessage])

  if (!hasHydrated) return null

  return (
    <div className="flex h-full flex-col terminal-container overflow-hidden">
      <Dialog open={Boolean(pendingFeedback)} onOpenChange={(open) => {
        if (!open) {
          closeFeedbackDialog()
        }
      }}>
        <DialogContent className={isPendingGoodFeedback
          ? 'border-emerald-500/30 bg-zinc-950 text-zinc-100 sm:max-w-md'
          : 'border-red-500/30 bg-zinc-950 text-zinc-100 sm:max-w-md'}>
          <DialogHeader>
            <DialogTitle className={isPendingGoodFeedback
              ? 'font-mono text-sm text-emerald-300'
              : 'font-mono text-sm text-red-300'}>
              {isPendingGoodFeedback ? 'Save good response' : 'Flag response'}
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              {isPendingGoodFeedback
                ? 'Add a short optional note so the saved example explains what worked.'
                : 'Add a short optional note so the saved report explains what was wrong.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {pendingFeedbackPresets.map((preset) => {
                const selected = feedbackNote === preset
                return (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setFeedbackNote(preset)}
                    disabled={isPendingFeedbackSaving}
                    className={selected
                      ? isPendingGoodFeedback
                        ? 'rounded border border-emerald-400/60 bg-emerald-500/20 px-2 py-1 font-mono text-[11px] text-emerald-100 transition-colors disabled:cursor-default disabled:opacity-60'
                        : 'rounded border border-red-400/60 bg-red-500/20 px-2 py-1 font-mono text-[11px] text-red-100 transition-colors disabled:cursor-default disabled:opacity-60'
                      : 'rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[11px] text-zinc-300 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60'}
                  >
                    {preset}
                  </button>
                )
              })}
            </div>
            <Textarea
              value={feedbackNote}
              onChange={(event) => setFeedbackNote(event.target.value.slice(0, 280))}
              placeholder={isPendingGoodFeedback
                ? 'Optional note, e.g. well grounded, strong evidence use, helpful synthesis'
                : 'Optional note, e.g. wrong ticker context, unsupported claim, bad math'}
              disabled={isPendingFeedbackSaving}
              maxLength={280}
              rows={4}
              className={isPendingGoodFeedback
                ? 'border-emerald-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500'
                : 'border-red-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500'}
            />
            <div className="text-right font-mono text-[11px] text-zinc-500">
              {feedbackNote.length}/280
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={closeFeedbackDialog}
              disabled={isPendingFeedbackSaving}
              className="rounded border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-200 transition-colors hover:bg-zinc-800 disabled:cursor-default disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleFeedbackSubmit()}
              disabled={isPendingFeedbackSaving}
              className={isPendingGoodFeedback
                ? 'rounded border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 font-mono text-xs text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:cursor-default disabled:opacity-60'
                : 'rounded border border-red-500/30 bg-red-500/10 px-3 py-2 font-mono text-xs text-red-200 transition-colors hover:bg-red-500/20 disabled:cursor-default disabled:opacity-60'}
            >
              {isPendingFeedbackSaving ? 'Saving...' : isPendingGoodFeedback ? 'Save good feedback' : 'Save flag'}
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
          cockpit@financial-ai ~ /chat
        </span>
        {/* Ticker context control */}
        {showTickerInput ? (
          <form
            className="flex items-center gap-1 ml-1"
            onSubmit={(e) => {
              e.preventDefault()
              const val = tickerDraft.trim().toUpperCase()
              if (val && val.length >= 2 && val.length <= 5) {
                setActiveTicker(val)
              }
              setTickerDraft('')
              setShowTickerInput(false)
            }}
          >
            <input
              type="text"
              autoFocus
              value={tickerDraft}
              onChange={(e) => setTickerDraft(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setTickerDraft('')
                  setShowTickerInput(false)
                }
              }}
              placeholder="ASX ticker"
              maxLength={5}
              className="w-16 bg-transparent border border-border/40 rounded px-1 py-0.5 font-mono text-[11px] text-emerald-400 placeholder:text-muted-foreground/40 focus:outline-none focus:border-emerald-500/50"
            />
            <button type="submit" className="font-mono text-[11px] text-emerald-400 hover:text-emerald-300">set</button>
            <button
              type="button"
              onClick={() => { setTickerDraft(''); setShowTickerInput(false) }}
              className="font-mono text-[11px] text-muted-foreground hover:text-foreground"
            >
              esc
            </button>
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setShowTickerInput(true)}
            className="font-mono text-[11px] ml-1 px-1.5 py-0.5 rounded border border-border/30 hover:border-border/60 transition-colors"
            title={activeTicker ? 'Click to change ticker' : 'Click to set ticker'}
          >
            {activeTicker ? (
              <span className="text-emerald-400">{activeTicker}</span>
            ) : (
              <span className="text-muted-foreground/60 italic">no ticker</span>
            )}
          </button>
        )}
        {activeTicker && !showTickerInput && (
          <button
            type="button"
            onClick={() => setActiveTicker('')}
            className="font-mono text-[10px] text-muted-foreground/50 hover:text-red-400 transition-colors"
            title="Clear ticker context"
          >
            ✕
          </button>
        )}
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
                showSources={preferences.showSources}
                onConfirmAction={handleConfirmAction}
                onCancelAction={handleCancelAction}
              />
              {msg.role === 'assistant' && (
                <div className="ml-6 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleFeedbackMessage(msg, 'good')}
                    disabled={Boolean(feedbackStates[msg.id])}
                    className="rounded border border-emerald-500/30 bg-emerald-500/8 px-2 py-0.5 font-mono text-[11px] text-emerald-300 transition-colors hover:bg-emerald-500/15 disabled:cursor-default disabled:opacity-70"
                  >
                    {getFeedbackButtonLabel('good', feedbackStates[msg.id])}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleFeedbackMessage(msg, 'poor')}
                    disabled={Boolean(feedbackStates[msg.id])}
                    className="rounded border border-red-500/30 bg-red-500/8 px-2 py-0.5 font-mono text-[11px] text-red-300 transition-colors hover:bg-red-500/15 disabled:cursor-default disabled:opacity-70"
                  >
                    {getFeedbackButtonLabel('poor', feedbackStates[msg.id])}
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
                showSources={preferences.showSources}
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
