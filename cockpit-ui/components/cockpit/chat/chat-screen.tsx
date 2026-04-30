'use client'

import { useState, useRef, useEffect, useCallback, type ChangeEvent, type DragEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
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
import { MessageClaimVerification } from './message-claim-verification'
import {
  IngestSummaryCard,
  type IngestSummary,
} from './ingest-summary-card'
import {
  TakeawaysPanel,
  type TakeawayCitation,
  type TakeawaysPayload,
} from './takeaways-panel'
import { SourcesDrawer } from './sources-drawer'
import { modelsLikelyMatch, parseCockpitConfig, resolveRuntimeModel } from '@/lib/cockpit-config'
import { useCockpitStore, generateId } from '@/lib/cockpit-store'
import {
  streamChat,
  sendChatMessage,
  restartBackend,
  startActionJob,
  getActionJob,
  getChatSessionMessages,
  deleteChatSessionRemote,
  type ActionJobStatus,
} from '@/lib/api-client'
import { deleteChatSession, loadChatSession, saveChatSession } from '@/lib/chat-session-store'
import { useAttachedSources } from '@/lib/hooks/use-attached-sources'
import {
  MARKETPLACE_CAPTURE_CHANNEL,
  isMarketplaceCaptureRelayResponse,
} from '@/lib/marketplace-capture-helper'
import {
  parseMarketplaceCaptureError,
  shouldOfferMarketplaceBrowserLaunch,
} from '@/lib/marketplace-bootstrap'
import { extractMarketplaceUrl } from '@/lib/marketplace-url'
import { extractYouTubeUrl } from '@/lib/youtube-url'
import { applyApiDefaultOverride, isApiRoutedMessage } from '@/lib/chat-routing'
import type { ChatMessage as ChatMessageType, ActionPreview, ChatProviderError } from '@/lib/cockpit-types'
import { toReportDisplayPath } from '@/lib/report-path'
import { toast } from 'sonner'

const MAX_CHAT_ATTACHMENT_BYTES = 25 * 1024 * 1024

function formatAttachmentLimit(bytes: number): string {
  return `${Math.floor(bytes / (1024 * 1024))} MiB`
}

type FeedbackKind = 'good' | 'poor'

type FeedbackState = 'saving-good' | 'saved-good' | 'saving-poor' | 'saved-poor'

type FeedbackCaptureResponse = {
  report_id: string
  feedback_type: FeedbackKind
  capture_kind?: 'chat_feedback' | 'ui_issue' | 'auto_diagnostic'
  report_dir: string
  read_api_path?: string | null
  codex_prompt?: string | null
  codex_prompt_path?: string | null
  investigation_path?: string | null
  investigation_status?: string | null
  codex_cli_command?: string | null
  analysis_summary?: string | null
}

type CodexDeployStatus = 'queued' | 'launching' | 'running' | 'completed' | 'failed' | 'not_requested' | 'error'

type CodexDeployState = {
  status: CodexDeployStatus
  detail?: string
}

type CodexDeployResponse = {
  ok?: boolean
  report_id?: string
  status?: string
  error?: string
  output_tail?: string | null
  stderr_tail?: string | null
  launcher_log_tail?: string | null
}

type PendingFeedback = {
  kind: FeedbackKind
  message: ChatMessageType
}

type WatchlistNotice = {
  tone: 'success' | 'error'
  text: string
}

type IngestUrlResponse = {
  source_id: string
  video_title?: string
  listing_title?: string
  source_name?: string
  webpage_url?: string
  staged?: boolean
  chunks_staged?: number
  chunks_indexed?: number
  detected_tickers?: string[]
  source_kind?: 'ephemeral' | 'concat' | 'primary'
}

type TakeawaysResponse = {
  source_id: string
  takeaways?: Array<{
    text: string
    citations?: Array<{
      chunk_id: string
      segment_start_seconds: number
    }>
  }>
  watchlist_suggestions?: Array<{
    ticker: string
    commentary: string
    citations?: Array<{
      chunk_id: string
      segment_start_seconds: number
    }>
  }>
  model?: string
  prompt_version?: string
}

type ChatAttachmentUploadResponse = {
  ok: boolean
  file_kind: 'holdings_csv' | 'strategy_pdf'
  message: string
  imported_count?: number
  skipped_count?: number
  errors?: string[]
  source_id?: string | null
  source_kind?: 'ephemeral' | 'concat' | 'primary' | null
  chunks_staged?: number
  key_points?: string[]
}

function bytesToBase64(bytes: Uint8Array): string {
  let output = ''
  const chunkSize = 0x8000
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize)
    output += String.fromCharCode(...chunk)
  }
  return btoa(output)
}

function buildProviderErrorNotice(providerError: ChatProviderError | null | undefined): string | null {
  if (!providerError || providerError.code !== 'billing_insufficient_credit') {
    return null
  }
  const message = String(providerError.message || '').trim()
  return message || 'Claude API credits are exhausted. Top up Anthropic credits in Plans & Billing.'
}

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

function formatFlagHandoffMessage(result: FeedbackCaptureResponse, copiedPrompt: boolean): string {
  const reportPath = toReportDisplayPath(result.report_dir) || result.report_dir
  const promptPath = result.codex_prompt_path
    ? (toReportDisplayPath(result.codex_prompt_path) || result.codex_prompt_path)
    : null
  const investigationPath = result.investigation_path
    ? (toReportDisplayPath(result.investigation_path) || result.investigation_path)
    : null
  const status = result.investigation_status || 'queued'
  const lines = [
    'Flag captured. Codex investigation is ready to deploy.',
    '',
    `Report: \`${reportPath}\``,
    `Status: \`${status}\``,
  ]
  if (promptPath) {
    lines.push(`Prompt file: \`${promptPath}\``)
  }
  if (investigationPath) {
    lines.push(`Investigation packet: \`${investigationPath}\``)
  }
  if (result.read_api_path) {
    lines.push(`Read API: \`${result.read_api_path}\``)
  }
  if (result.codex_cli_command) {
    lines.push('', 'Deploy Codex from the repo root:', '```bash', result.codex_cli_command, '```')
  }
  if (result.report_id) {
    lines.push('', 'Press **Deploy Codex** to start this investigation from Cockpit.')
  }
  const prompt = result.codex_prompt?.trim()
  if (prompt) {
    lines.push(
      '',
      copiedPrompt
        ? 'The Codex prompt has been copied to your clipboard. Prompt body:'
        : 'Copy this prompt into a Codex CLI session:',
      '```text',
      prompt,
      '```',
    )
  }
  return lines.join('\n')
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

function resolveResponseLatencyMs(rawLatencyMs: unknown, startedAtMs: number | null): number | undefined {
  const latencyMs =
    typeof rawLatencyMs === 'number'
      ? rawLatencyMs
      : (typeof rawLatencyMs === 'string' ? Number(rawLatencyMs) : Number.NaN)

  if (Number.isFinite(latencyMs) && latencyMs > 0) {
    return Math.round(latencyMs)
  }

  if (startedAtMs === null) {
    return undefined
  }

  return Math.max(1, Date.now() - startedAtMs)
}

function toChatMessage(record: {
  id?: number
  role?: string
  content?: string
  created_at?: string
}): ChatMessageType {
  const role = record.role === 'user' || record.role === 'assistant' || record.role === 'system'
    ? record.role
    : 'system'
  const parsed = new Date(record.created_at || '')
  return {
    id: typeof record.id === 'number' ? `srv-${record.id}` : generateId(),
    role,
    content: String(record.content || ''),
    timestamp: Number.isNaN(parsed.getTime()) ? new Date() : parsed,
  }
}

export function ChatScreen() {
  const attached = useAttachedSources()
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
  const [latestIngest, setLatestIngest] = useState<IngestSummary | null>(null)
  const [latestVideoUrl, setLatestVideoUrl] = useState<string | null>(null)
  const [takeaways, setTakeaways] = useState<TakeawaysPayload | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [watchlistNotice, setWatchlistNotice] = useState<WatchlistNotice | null>(null)
  const [isDropActive, setIsDropActive] = useState(false)
  const [codexDeployStates, setCodexDeployStates] = useState<Record<string, CodexDeployState>>({})
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dragDepthRef = useRef(0)
  const activeStreamRef = useRef<{ close: () => void } | null>(null)
  const activeRequestStartedAtRef = useRef<number | null>(null)
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

  // Wait for hydration to finish to avoid SSR/CSR mismatch with Zustand.
  useEffect(() => {
    setHasHydrated(true)
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  // Load session messages from backend so chat history follows session_id across devices.
  useEffect(() => {
    if (!hasHydrated) return
    let cancelled = false
    ;(async () => {
      try {
        const remoteMessages = await getChatSessionMessages(sessionId, 600)
        if (cancelled) return
        setMessages(remoteMessages.map(toChatMessage))
      } catch {
        // Backend unavailable: keep local cache path for resilience.
        const persisted = loadChatSession(sessionId)
        if (!cancelled) {
          setMessages(persisted.messages)
        }
      } finally {
        if (!cancelled) {
          // We don't want to clear takeaways/ingest immediately if they are
          // session-bound, but typically a session change means a fresh view.
          setLatestIngest(null)
          setTakeaways(null)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [sessionId, hasHydrated])

  // Persist messages to localStorage whenever they change so the chat survives
  // route changes (ChatScreen unmounts when the user navigates away).
  useEffect(() => {
    if (!hasHydrated) return
    // Only save if we have a valid session and at least some messages or an active ticker
    // to avoid creating empty "zombie" sessions in the list if the user just clicks around.
    if (messages.length === 0 && !activeTicker) return

    saveChatSession({
      sessionId,
      activeTicker,
      draft: '',
      messages,
      updatedAt: new Date().toISOString(),
    })
  }, [messages, sessionId, activeTicker, hasHydrated])

  const appendSystemMessage = useCallback((content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: generateId(),
        role: 'system',
        content,
        timestamp: new Date(),
      },
    ])
  }, [])

  const buildAuthHeaders = useCallback(
    (contentType?: string): Record<string, string> => {
      const headers: Record<string, string> = {}
      if (contentType) {
        headers['Content-Type'] = contentType
      }
      if (apiKey) {
        headers['X-API-Key'] = apiKey
      }
      return headers
    },
    [apiKey],
  )

  const openCitation = useCallback((citation: TakeawayCitation) => {
    if (!latestVideoUrl || typeof window === 'undefined') {
      return
    }

    try {
      const link = new URL(latestVideoUrl)
      link.searchParams.set('t', `${Math.max(0, Math.floor(citation.segmentStartSeconds))}s`)
      window.open(link.toString(), '_blank', 'noopener,noreferrer')
    } catch {
      // Ignore malformed URLs and preserve the rest of the chat flow.
    }
  }, [latestVideoUrl])

  const addTickerToWatchlist = useCallback(async (ticker: string, commentary?: string) => {
    try {
      const response = await fetch('/api/cockpit/watchlist', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({
          ticker,
          source_id: latestIngest?.sourceId ?? null,
          note: commentary ?? null,
          stance: 'watch',
        }),
      })

      if (response.status === 409) {
        const text = `${ticker} is already in watchlist`
        setWatchlistNotice({ tone: 'error', text })
        toast.error(text)
        return
      }

      if (!response.ok) {
        const text = `Failed to add ${ticker} to watchlist (${response.status})`
        setWatchlistNotice({ tone: 'error', text })
        toast.error(text)
        return
      }

      const text = `Added ${ticker} to watchlist`
      setWatchlistNotice({ tone: 'success', text })
      toast.success(text)
    } catch (error) {
      const text = error instanceof Error ? error.message : 'Watchlist request failed'
      setWatchlistNotice({ tone: 'error', text })
      toast.error(text)
    }
  }, [buildAuthHeaders, latestIngest?.sourceId])

  const fetchTakeaways = useCallback(async (sourceId: string, videoUrl: string | null) => {
    try {
      const response = await fetch('/api/cockpit/commentary/takeaways', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({ source_id: sourceId }),
      })
      if (!response.ok) {
        return
      }

      const payload = (await response.json()) as TakeawaysResponse
      setTakeaways({
        sourceId: payload.source_id,
        videoId: videoUrl ?? sourceId,
        takeaways: (payload.takeaways || []).map((takeaway) => ({
          text: takeaway.text,
          citations: (takeaway.citations || []).map((citation) => ({
            chunkId: citation.chunk_id,
            segmentStartSeconds: citation.segment_start_seconds,
          })),
        })),
        watchlistSuggestions: (payload.watchlist_suggestions || []).map((suggestion) => ({
          ticker: suggestion.ticker,
          commentary: suggestion.commentary,
          citations: (suggestion.citations || []).map((citation) => ({
            chunkId: citation.chunk_id,
            segmentStartSeconds: citation.segment_start_seconds,
          })),
        })),
        model: payload.model || 'unknown',
        promptVersion: payload.prompt_version || 'unknown',
      })
    } catch {
      // Keep the paste-to-ingest flow usable even when takeaways are unavailable.
    }
  }, [buildAuthHeaders])

  const applyMarketplaceIngest = useCallback((body: IngestUrlResponse, url: string, systemMessage?: string) => {
    const summary: IngestSummary = {
      sourceId: body.source_id,
      title: body.listing_title || body.source_name || 'Facebook Marketplace listing',
      chunkCount: body.chunks_staged ?? body.chunks_indexed ?? 0,
      detectedTickers: Array.isArray(body.detected_tickers) ? body.detected_tickers : [],
      status: body.staged === false ? 'approved' : 'pending',
      sourceKind: body.source_kind ?? 'concat',
    }

    setLatestIngest(summary)
    setLatestVideoUrl(body.webpage_url ?? url)
    setTakeaways(null)
    setWatchlistNotice(null)
    attached.attach({
      sourceId: body.source_id,
      sourceKind: summary.sourceKind,
      title: summary.title,
    })
    if (systemMessage) {
      appendSystemMessage(systemMessage)
    }
    toast.success(`Captured ${summary.title}`)
  }, [appendSystemMessage, attached])

  const buildEphemeralIndex = useCallback(async (sourceId: string) => {
    try {
      await fetch('/api/cockpit/commentary/ephemeral-index', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({
          session_id: sessionId,
          source_ids: [sourceId],
        }),
      })
    } catch {
      // Session-scoped indexing is opportunistic from the UI's perspective.
    }
  }, [buildAuthHeaders, sessionId])

  const uploadAttachmentFiles = useCallback(async (files: File[]) => {
    if (files.length === 0) {
      return
    }

    for (const file of files) {
      const filename = String(file.name || 'uploaded-file').trim() || 'uploaded-file'
      const lower = filename.toLowerCase()
      const isCsv = lower.endsWith('.csv') || file.type.toLowerCase().includes('csv')
      const isXlsx = lower.endsWith('.xlsx') || lower.endsWith('.xlsm') || file.type.toLowerCase().includes('spreadsheetml')
      const isPdf = lower.endsWith('.pdf') || file.type.toLowerCase().includes('pdf')
      const isTabular = isCsv || isXlsx
      if (!isTabular && !isPdf) {
        appendSystemMessage(`Unsupported file "${filename}". Upload CSV, XLSX, or PDF files only.`)
        toast.error(`Unsupported file: ${filename}`)
        continue
      }
      if (file.size > MAX_CHAT_ATTACHMENT_BYTES) {
        const limit = formatAttachmentLimit(MAX_CHAT_ATTACHMENT_BYTES)
        const message = `Attachment "${filename}" is too large. Upload files up to ${limit}.`
        appendSystemMessage(message)
        toast.error(message)
        continue
      }

      try {
        const bytes = new Uint8Array(await file.arrayBuffer())
        const contentBase64 = bytesToBase64(bytes)
        const csvProfile = isTabular && /\btrade(s)?\b/.test(lower) ? 'trades' : 'auto'
        const csvStrict = csvProfile === 'trades'
        const response = await fetch('/api/cockpit/chat/attachments/upload', {
          method: 'POST',
          headers: buildAuthHeaders('application/json'),
          body: JSON.stringify({
            filename,
            mime_type: file.type || null,
            content_base64: contentBase64,
            csv_profile: csvProfile,
            csv_strict: csvStrict,
          }),
        })

        const rawBody = await response.text()
        let payload: ChatAttachmentUploadResponse | null = null
        if (rawBody) {
          try {
            payload = JSON.parse(rawBody) as ChatAttachmentUploadResponse
          } catch {
            payload = null
          }
        }
        if (!response.ok || payload === null) {
          const detail = payload && typeof payload === 'object'
            ? String((payload as { detail?: string }).detail || '')
            : rawBody
          if (response.status === 404 && /not found/i.test(detail)) {
            throw new Error(
              'Attachment upload endpoint is unavailable on the backend. Restart backend to load /api/cockpit/chat/attachments/upload.'
            )
          }
          throw new Error(detail || `Attachment upload failed (${response.status})`)
        }

        if (payload.file_kind === 'holdings_csv') {
          const imported = Number(payload.imported_count || 0)
          const skipped = Number(payload.skipped_count || 0)
          const errors = Array.isArray(payload.errors) ? payload.errors : []
          const errorSummary = errors.length > 0 ? `\nIssues:\n- ${errors.slice(0, 5).join('\n- ')}` : ''
          appendSystemMessage(
            `${payload.message || `Imported ${imported} holdings from ${filename}.`}\nImported: ${imported}\nSkipped: ${skipped}${errorSummary}`
          )
          toast.success(`Imported holdings from ${filename}`)
          continue
        }

        const sourceId = String(payload.source_id || '').trim()
        const sourceKind = payload.source_kind || 'concat'
        const stagedChunks = Number(payload.chunks_staged || 0)
        const keyPoints = Array.isArray(payload.key_points) ? payload.key_points.slice(0, 5) : []
        if (sourceId) {
          attached.attach({
            sourceId,
            sourceKind,
            title: filename,
          })
          await buildEphemeralIndex(sourceId)
          setLatestIngest({
            sourceId,
            title: filename,
            chunkCount: stagedChunks,
            detectedTickers: [],
            status: 'pending',
            sourceKind,
          })
          setLatestVideoUrl(null)
          setTakeaways(null)
          setWatchlistNotice(null)
        }

        const pointsSection = keyPoints.length > 0 ? `\nKey points:\n- ${keyPoints.join('\n- ')}` : ''
        appendSystemMessage(`${payload.message || `Attached ${filename}.`}${pointsSection}`)
        toast.success(`Attached ${filename}`)
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Attachment upload failed'
        appendSystemMessage(`Attachment upload failed for ${filename}: ${message}`)
        toast.error(message)
      }
    }
  }, [appendSystemMessage, attached, buildAuthHeaders, buildEphemeralIndex])

  const ingestYouTubeUrl = useCallback(async (url: string) => {
    try {
      const response = await fetch('/api/commentary/ingest-url', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({ url }),
      })

      if (!response.ok) {
        const detail = await response.text()
        const message = detail || `Ingest failed (${response.status})`
        appendSystemMessage(`YouTube ingest failed: ${message}`)
        toast.error(message)
        return
      }

      const body = (await response.json()) as IngestUrlResponse
      const summary: IngestSummary = {
        sourceId: body.source_id,
        title: body.video_title || body.source_name || 'YouTube transcript',
        chunkCount: body.chunks_staged ?? body.chunks_indexed ?? 0,
        detectedTickers: Array.isArray(body.detected_tickers) ? body.detected_tickers : [],
        status: body.staged === false ? 'approved' : 'pending',
        sourceKind: 'ephemeral',
      }

      setLatestIngest(summary)
      setLatestVideoUrl(body.webpage_url ?? url)
      setTakeaways(null)
      setWatchlistNotice(null)
      attached.attach({
        sourceId: body.source_id,
        sourceKind: summary.sourceKind,
        title: summary.title,
      })
      toast.success(`Ingested ${summary.title}`)

      await Promise.allSettled([
        fetchTakeaways(body.source_id, body.webpage_url ?? url),
        buildEphemeralIndex(body.source_id),
      ])
    } catch (error) {
      const message = error instanceof Error ? error.message : 'YouTube ingest failed'
      appendSystemMessage(`YouTube ingest failed: ${message}`)
      toast.error(message)
    }
  }, [appendSystemMessage, attached, buildAuthHeaders, buildEphemeralIndex, fetchTakeaways])

  const openMarketplaceCaptureHelper = useCallback(async (url: string) => {
    try {
      const response = await fetch('/api/cockpit/commentary/marketplace-capture/token', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({ url }),
      })
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(detail || `Marketplace helper failed (${response.status})`)
      }
      const body = (await response.json()) as { token?: string }
      const token = String(body.token || '').trim()
      if (!token) {
        throw new Error('Marketplace helper did not return a capture token')
      }
      const helperUrl = `/marketplace-capture?token=${encodeURIComponent(token)}&url=${encodeURIComponent(url)}`
      if (typeof window !== 'undefined') {
        const helperWindow = window.open(helperUrl, '_blank', 'noopener,noreferrer')
        if (!helperWindow) {
          window.location.assign(helperUrl)
        }
      }
      appendSystemMessage('Marketplace browser helper opened. Use the bookmarklet on the Facebook listing page to capture it.')
      toast.success('Marketplace helper opened')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Marketplace helper launch failed'
      appendSystemMessage(`Marketplace helper launch failed: ${message}`)
      toast.error(message)
    }
  }, [appendSystemMessage, buildAuthHeaders])

  const inspectMarketplaceUrl = useCallback(async (url: string) => {
    try {
      const response = await fetch('/api/commentary/inspect-marketplace', {
        method: 'POST',
        headers: buildAuthHeaders('application/json'),
        body: JSON.stringify({ url }),
      })

      if (!response.ok) {
        const detail = await response.text()
        const failure = parseMarketplaceCaptureError(detail, response.status)
        const message = failure.message || `Marketplace capture failed (${response.status})`
        appendSystemMessage(`Marketplace capture failed: ${message}`)
        if (shouldOfferMarketplaceBrowserLaunch(failure.kind)) {
          toast.error(message, {
            action: {
              label: 'Open Helper',
              onClick: () => {
                void openMarketplaceCaptureHelper(url)
              },
            },
          })
        } else {
          toast.error(message)
        }
        return
      }

      const body = (await response.json()) as IngestUrlResponse
      applyMarketplaceIngest(body, url)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Marketplace capture failed'
      appendSystemMessage(`Marketplace capture failed: ${message}`)
      toast.error(message)
    }
  }, [appendSystemMessage, applyMarketplaceIngest, buildAuthHeaders, openMarketplaceCaptureHelper])

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
      activeRequestStartedAtRef.current = null
      setChatCompletionActive(false)
      if (statusFallbackTimersRef.current.length > 0) {
        statusFallbackTimersRef.current.forEach((timerId) => window.clearTimeout(timerId))
        statusFallbackTimersRef.current = []
      }
    }
  }, [setChatCompletionActive])

  useEffect(() => {
    if (typeof window === 'undefined' || typeof BroadcastChannel === 'undefined') {
      return
    }
    const channel = new BroadcastChannel(MARKETPLACE_CAPTURE_CHANNEL)
    channel.onmessage = (event: MessageEvent<unknown>) => {
      if (!isMarketplaceCaptureRelayResponse(event.data)) {
        return
      }
      if (!event.data.ok) {
        appendSystemMessage(`Marketplace helper failed: ${event.data.message}`)
        toast.error(event.data.message)
        return
      }
      const ingest = event.data.ingest as IngestUrlResponse
      applyMarketplaceIngest(
        ingest,
        ingest.webpage_url ?? '',
        'Marketplace capture received from browser helper.',
      )
    }
    return () => {
      channel.close()
    }
  }, [appendSystemMessage, applyMarketplaceIngest])

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
    // Status labels that already carry their own elapsed time (e.g.
    // "Local model generating: N token chunks / 12s") should not get a second
    // timer appended — the inner counter is the authoritative one.
    if (/\/\s*\d+\s*s$/.test(label)) {
      return label
    }
    const elapsedMs = Math.max(0, streamingClockMs - streamingStatusStartedAt)
    return `${label} (${(elapsedMs / 1000).toFixed(1)}s)`
  }, [isStreaming, streamingClockMs, streamingStatus, streamingStatusStartedAt])

  const streamingLatencyMs = (
    isStreaming
    && activeRequestStartedAtRef.current !== null
  )
    ? Math.max(1, streamingClockMs - activeRequestStartedAtRef.current)
    : undefined

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

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFilePickerChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : []
    event.target.value = ''
    if (files.length === 0) {
      return
    }
    void uploadAttachmentFiles(files)
  }, [uploadAttachmentFiles])

  const handleDragEnter = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer?.types.includes('Files')) {
      return
    }
    event.preventDefault()
    event.stopPropagation()
    dragDepthRef.current += 1
    setIsDropActive(true)
  }, [])

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer?.types.includes('Files')) {
      return
    }
    event.preventDefault()
    event.stopPropagation()
    if (!isDropActive) {
      setIsDropActive(true)
    }
  }, [isDropActive])

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer?.types.includes('Files')) {
      return
    }
    event.preventDefault()
    event.stopPropagation()
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
    if (dragDepthRef.current === 0) {
      setIsDropActive(false)
    }
  }, [])

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    dragDepthRef.current = 0
    setIsDropActive(false)
    const files = event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : []
    if (files.length === 0) {
      return
    }
    void uploadAttachmentFiles(files)
  }, [uploadAttachmentFiles])

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

    if (!content.startsWith('/')) {
      const marketplaceUrl = extractMarketplaceUrl(content)
      if (marketplaceUrl) {
        await inspectMarketplaceUrl(marketplaceUrl)
        return
      }
      const detectedUrl = extractYouTubeUrl(content)
      if (detectedUrl) {
        await ingestYouTubeUrl(detectedUrl)
        return
      }
    }

    clearStatusFallbackTimers()
    receivedServerStatusRef.current = false
    setIsStreaming(true)
    setChatCompletionActive(true)
    setStreamingContent('')
    const outboundMessage = applyApiDefaultOverride(content, apiDefaultEnabled)
    const apiRoutedMessage = isApiRoutedMessage(outboundMessage)
    const modelForRequest = apiRoutedMessage ? undefined : chatModel
    const requestedModel = apiRoutedMessage ? '' : String(chatModel || '').trim()
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
    const requestStartedAt = Date.now()
    activeRequestStartedAtRef.current = requestStartedAt

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
            metadata: {
              source: 'local',
              latencyMs: resolveResponseLatencyMs(undefined, requestStartedAt),
            },
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
          activeRequestStartedAtRef.current = null
        }
        return
      }

      try {
        const response = await sendChatMessage({
          message: outboundMessage,
          mode: 'analysis',
          ticker: activeTicker || undefined,
          sessionId: sessionId,
          model: modelForRequest,
          webSearch: preferences.webSearchEnabled,
          rag: preferences.ragEnabled,
        dbDiagnostics: preferences.dbDiagnosticsEnabled,
        attachedSources: attached.serialize(),
      })

        const latencyMs = resolveResponseLatencyMs(response.content.latency_ms, requestStartedAt)
        const systemMessage: ChatMessageType = {
          id: generateId(),
          role: 'assistant',
          content: response.content.answer,
          timestamp: new Date(),
          metadata: {
            model: response.content.model,
            latencyMs,
            costUsd: response.content.cost_usd || 0,
            source: response.content.source || 'local'
          },
          sources: response.content.sources,
          chart: response.content.chart,
        }
        if (response.content.cost_usd) addCost(response.content.cost_usd)
        if (latencyMs !== undefined) setLatency(latencyMs)
	        if (response.content.model) setActiveModel(response.content.model)
	        setActiveSource(response.content.source || 'local')
	        const providerErrorNotice = buildProviderErrorNotice(response.content.provider_error)
	        if (providerErrorNotice) {
	          toast.error(providerErrorNotice, { duration: 15000 })
	          setMessages(prev => [...prev, systemMessage, {
	            id: generateId(),
	            role: 'system',
	            content: providerErrorNotice,
	            timestamp: new Date(),
	          }])
	        } else {
	          setMessages(prev => [...prev, systemMessage])
	        }
	      } catch (err) {
        toast.error('Command failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
      } finally {
        setIsStreaming(false)
        setChatCompletionActive(false)
        activeRequestStartedAtRef.current = null
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
        model: modelForRequest,
        webSearch: preferences.webSearchEnabled,
        rag: preferences.ragEnabled,
        dbDiagnostics: preferences.dbDiagnosticsEnabled,
        attachedSources: attached.serialize(),
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
              const latencyMs = resolveResponseLatencyMs(event.data.latency_ms, requestStartedAt)
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
                  latencyMs,
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
              if (latencyMs !== undefined) setLatency(latencyMs)
              if (event.data.model) setActiveModel(event.data.model)
              setActiveSource(event.data.source || 'local')
              setPendingActionPreview(normalizedActionPreview ?? null)

              const autoFlag = event.data?.auto_flag && typeof event.data.auto_flag === 'object'
                ? event.data.auto_flag as FeedbackCaptureResponse
                : null
              const autoFlagMessage: ChatMessageType | null = autoFlag
                ? {
                    id: generateId(),
	                    role: 'system',
	                    content: formatFlagHandoffMessage(autoFlag, false),
	                    timestamp: new Date(),
	                    metadata: {
	                      source: 'cockpit',
	                      codexDeploy: { reportId: autoFlag.report_id },
	                    },
	                  }
	                : null
              const providerErrorNotice = buildProviderErrorNotice(event.data?.provider_error)
              if (providerErrorNotice) {
                toast.error(providerErrorNotice, { duration: 15000 })
                setMessages(prev => [
                  ...prev,
                  assistantMessage,
                  ...(autoFlagMessage ? [autoFlagMessage] : []),
                  {
                    id: generateId(),
                    role: 'system',
                    content: providerErrorNotice,
                    timestamp: new Date(),
                  },
                ])
              } else {
                setMessages(prev => [
                  ...prev,
                  assistantMessage,
                  ...(autoFlagMessage ? [autoFlagMessage] : []),
                ])
              }
              if (autoFlagMessage) {
                toast.success('Flag captured. Codex investigation is ready to deploy.')
              }
              setStreamingContent('')
              clearStreamingStage()
              setStreamingMetadata({})
              setIsStreaming(false)
              setChatCompletionActive(false)
              clearStatusFallbackTimers()
              activeStreamRef.current = null
              activeRequestStartedAtRef.current = null
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
              activeRequestStartedAtRef.current = null
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
          activeRequestStartedAtRef.current = null
        },
        onEnd: () => {
          if (!streamFinalized) {
            const fallbackText = currentContent.trim()
            const latencyMs = resolveResponseLatencyMs(undefined, requestStartedAt)
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
                metadata: {
                  source: 'local',
                  latencyMs,
                },
                thinking: currentMetadata.thinking,
                sources: currentMetadata.sources,
                toolTraces: normalizedActionPreview ? [] : currentMetadata.toolTraces,
                actionPreview: normalizedActionPreview,
              }])
              if (latencyMs !== undefined) setLatency(latencyMs)
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
          activeRequestStartedAtRef.current = null
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
      activeRequestStartedAtRef.current = null
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
    const isCandlestickAction = actionId === 'show_candlestick'
    const hasRenderableChart = (chart: ChatMessageType['chart'] | null | undefined): chart is NonNullable<ChatMessageType['chart']> => (
      Boolean(chart && typeof chart.html === 'string' && chart.html.trim())
    )
    const missingChartDetail = (raw: string | null | undefined): string => {
      const detail = String(raw || '').trim()
      return detail
        ? `missing rendered chart payload (${detail})`
        : 'missing rendered chart payload'
    }

    const progressMessageId = generateId()
    const renderProgressContent = (status: ActionJobStatus | null, fallbackStatus: string): string => {
      const stage = status?.progress_stage?.trim()
      const pct = typeof status?.progress_pct === 'number' ? status.progress_pct : null
      const pctLabel = pct !== null ? ` — ${Math.round(pct)}%` : ''
      const statusLabel = status?.status ?? fallbackStatus
      const stageLabel = stage ? `\n\n_Stage: ${stage}${pctLabel}_` : (pctLabel ? `\n\n_${pctLabel.replace(/^ — /, '')}_` : '')
      return `Running **${actionPreview.name}**… (status: ${statusLabel})${stageLabel}`
    }

    setMessages(prev => [...prev, {
      id: progressMessageId,
      role: 'system',
      content: renderProgressContent(null, 'starting'),
      timestamp: new Date(),
      metadata: { source: 'local' },
    }])

    const terminalStatuses = new Set(['completed', 'failed', 'cancelled', 'error', 'timeout'])
    const pollIntervalMs = 1000
    const pollTimeoutMs = 15 * 60 * 1000  // 15-minute hard cap on UI polling

    try {
      const handle = await startActionJob({
        actionId,
        args: actionPreview.args,
        sessionId,
      })

      if (!handle.job_id) {
        if (isCandlestickAction && !hasRenderableChart(handle.chart)) {
          const detail = missingChartDetail(handle.result)
          setMessages(prev => prev.map(m => m.id === progressMessageId
            ? {
                ...m,
                role: 'system',
                content: `Action **${actionPreview.name}** failed: ${detail}`,
                timestamp: new Date(),
              }
            : m))
          toast.error(`Action "${actionPreview.name}" failed`)
          return
        }
        const finalContent = handle.result
          ? `Action **${actionPreview.name}** executed successfully.\n\n${handle.result}`
          : `Action **${actionPreview.name}** executed successfully.`
        setMessages(prev => prev.map(m => m.id === progressMessageId
          ? { ...m, role: 'assistant', content: finalContent, timestamp: new Date(), metadata: { source: 'local' }, chart: handle.chart ?? undefined }
          : m))
        toast.success(`Action "${actionPreview.name}" executed`)
        return
      }

      setMessages(prev => prev.map(m => m.id === progressMessageId
        ? { ...m, content: renderProgressContent(null, handle.status || 'queued') }
        : m))

      const pollStart = Date.now()
      let lastStatus: ActionJobStatus | null = null
      while (Date.now() - pollStart < pollTimeoutMs) {
        await new Promise(resolve => setTimeout(resolve, pollIntervalMs))
        try {
          lastStatus = await getActionJob(handle.job_id)
        } catch {
          // Transient poll failures (network blip) should not kill the action — keep trying.
          continue
        }
        setMessages(prev => prev.map(m => m.id === progressMessageId
          ? { ...m, content: renderProgressContent(lastStatus, lastStatus?.status ?? 'running') }
          : m))
        if (lastStatus && terminalStatuses.has(lastStatus.status)) {
          break
        }
      }

      if (!lastStatus || !terminalStatuses.has(lastStatus.status)) {
        setMessages(prev => prev.map(m => m.id === progressMessageId
          ? {
              ...m,
              role: 'system',
              content: `Action **${actionPreview.name}** is still running in the background. Check the jobs panel for final status.`,
              timestamp: new Date(),
            }
          : m))
        toast.info(`Action "${actionPreview.name}" still running — continuing in background`)
        return
      }

      if (lastStatus.status === 'completed') {
        const statusChart = (lastStatus as ActionJobStatus & { chart?: ChatMessageType['chart'] }).chart
        if (isCandlestickAction && !hasRenderableChart(statusChart)) {
          const detail = missingChartDetail(lastStatus.result)
          setMessages(prev => prev.map(m => m.id === progressMessageId
            ? {
                ...m,
                role: 'system',
                content: `Action **${actionPreview.name}** failed: ${detail}`,
                timestamp: new Date(),
              }
            : m))
          toast.error(`Action "${actionPreview.name}" failed`)
          return
        }
        const body = lastStatus.result?.trim()
        const finalContent = body
          ? `Action **${actionPreview.name}** executed successfully.\n\n${body}`
          : `Action **${actionPreview.name}** executed successfully.`
        setMessages(prev => prev.map(m => m.id === progressMessageId
          ? { ...m, role: 'assistant', content: finalContent, timestamp: new Date(), metadata: { source: 'local' }, chart: statusChart }
          : m))
        toast.success(`Action "${actionPreview.name}" executed`)
      } else {
        const detail = lastStatus.result?.trim() || `exit code ${lastStatus.exit_code ?? 'unknown'}`
        setMessages(prev => prev.map(m => m.id === progressMessageId
          ? {
              ...m,
              role: 'system',
              content: `Action **${actionPreview.name}** ${lastStatus.status}: ${detail}`,
              timestamp: new Date(),
            }
          : m))
        toast.error(`Action "${actionPreview.name}" ${lastStatus.status}`)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      setMessages(prev => prev.map(m => m.id === progressMessageId
        ? {
            ...m,
            role: 'system',
            content: `Action "${actionPreview.name}" failed: ${errorMsg}`,
            timestamp: new Date(),
          }
        : m))
      toast.error(`Action failed: ${errorMsg}`)
    } finally {
      actionInFlightRef.current = false
    }
  }, [sessionId])

  const handleDeployCodexFlag = useCallback(async (reportId: string) => {
    const normalizedReportId = String(reportId || '').trim()
    if (!normalizedReportId) {
      return
    }
    const existingStatus = codexDeployStates[normalizedReportId]?.status
    if (existingStatus === 'launching' || existingStatus === 'running' || existingStatus === 'completed') {
      return
    }

    const updateDeployState = (status: CodexDeployStatus, detail?: string) => {
      setCodexDeployStates((prev) => ({
        ...prev,
        [normalizedReportId]: { status, detail },
      }))
    }
    const readPayload = async (response: Response): Promise<CodexDeployResponse> => {
      const payload = await response.json().catch(() => null) as CodexDeployResponse | null
      if (!response.ok) {
        throw new Error(payload?.error || `HTTP ${response.status}`)
      }
      return payload || {}
    }
    const pollStatus = async () => {
      const startedAt = Date.now()
      const terminalStatuses = new Set(['completed', 'failed', 'error', 'not_requested'])
      while (Date.now() - startedAt < 30 * 60 * 1000) {
        await new Promise(resolve => setTimeout(resolve, 1500))
        const response = await fetch(`/api/cockpit/feedback/flags/${encodeURIComponent(normalizedReportId)}/investigation`, {
          cache: 'no-store',
        })
        const payload = await readPayload(response)
        const status = String(payload.status || 'unknown') as CodexDeployStatus
        updateDeployState(status === 'queued' ? 'launching' : status, payload.error)
        if (terminalStatuses.has(status)) {
          const detail = payload.output_tail?.trim() || payload.stderr_tail?.trim() || payload.launcher_log_tail?.trim() || ''
          setMessages((prev) => [...prev, {
            id: generateId(),
            role: status === 'completed' ? 'assistant' : 'system',
            content: status === 'completed'
              ? `Codex investigation completed for \`${normalizedReportId}\`.\n\n${detail || 'Review the report artifact for the final message.'}`
              : `Codex investigation ${status} for \`${normalizedReportId}\`.\n\n${detail || 'Check the report artifact for details.'}`,
            timestamp: new Date(),
            metadata: { source: 'cockpit' },
          }])
          if (status === 'completed') {
            toast.success('Codex investigation completed')
          } else {
            toast.error(`Codex investigation ${status}`)
          }
          return
        }
      }
      updateDeployState('running', 'Still running in the background')
      toast.info('Codex investigation is still running in the background')
    }

    try {
      updateDeployState('launching')
      const response = await fetch(`/api/cockpit/feedback/flags/${encodeURIComponent(normalizedReportId)}/deploy`, {
        method: 'POST',
        cache: 'no-store',
      })
      const payload = await readPayload(response)
      const status = String(payload.status || 'launching') as CodexDeployStatus
      updateDeployState(status === 'queued' ? 'launching' : status, payload.error)
      toast.success('Codex investigation deployed')
      void pollStatus()
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      updateDeployState('error', message)
      toast.error(`Failed to deploy Codex: ${message}`)
    }
  }, [codexDeployStates])

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

  const handleClearMessages = useCallback(async () => {
    try {
      await deleteChatSessionRemote(sessionId)
    } catch {
      // Keep local clear available when backend is unavailable.
    }
    deleteChatSession(sessionId)
    setMessages([])
    setStreamingContent('')
    setStreamingMetadata({})
      setFeedbackStates({})
      setPendingFeedback(null)
      setFeedbackNote('')
      setLatestIngest(null)
      setLatestVideoUrl(null)
      setTakeaways(null)
      setSourcesOpen(false)
      setWatchlistNotice(null)
      attached.clear()
  }, [attached, sessionId])

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
      const reportPath = toReportDisplayPath(result.report_dir) || result.report_dir

      if (feedbackType === 'good') {
        toast.success(result.analysis_summary?.trim()
          ? `Good response saved: ${result.analysis_summary}`
          : `Good response saved to ${reportPath}`)
      } else {
        const copiedPrompt = result.codex_prompt?.trim()
          ? await copyFlagPromptToClipboard(result.codex_prompt)
          : false
        setMessages((prev) => [...prev, {
          id: generateId(),
          role: 'system',
          content: formatFlagHandoffMessage(result, copiedPrompt),
          timestamp: new Date(),
          metadata: {
            source: 'cockpit',
            codexDeploy: { reportId: result.report_id },
          },
        }])
        toast.success(result.analysis_summary?.trim()
          ? copiedPrompt
            ? `Flag saved and Codex prompt copied: ${result.analysis_summary}`
            : `Flag saved: ${result.analysis_summary}`
          : copiedPrompt
            ? `Flag saved and Codex prompt copied: ${reportPath}`
            : `Flag saved to ${reportPath}`)
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
  const canClearChat = (
    messages.length > 0
    || Boolean(streamingContent)
    || attached.attached.length > 0
    || latestIngest !== null
    || takeaways !== null
    || watchlistNotice !== null
  )

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
    <div
      className={`flex h-full flex-col terminal-container overflow-hidden ${isDropActive ? 'ring-2 ring-blue-500/60 ring-inset' : ''}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,text/csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.pdf,application/pdf"
        className="hidden"
        onChange={handleFilePickerChange}
      />
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
              onChange={(event) => setFeedbackNote(event.target.value.slice(0, 2000))}
              placeholder={isPendingGoodFeedback
                ? 'Optional note, e.g. well grounded, strong evidence use, helpful synthesis'
                : 'Optional note, e.g. wrong ticker context, unsupported claim, bad math'}
              disabled={isPendingFeedbackSaving}
              maxLength={2000}
              rows={4}
              className={isPendingGoodFeedback
                ? 'border-emerald-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500'
                : 'border-red-500/20 bg-black/30 font-mono text-sm text-zinc-100 placeholder:text-zinc-500'}
            />
            <div className="text-right font-mono text-[11px] text-zinc-500">
              {feedbackNote.length}/2000
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

      {isDropActive ? (
        <div className="border-b border-blue-500/40 bg-blue-500/10 px-4 py-2 text-xs font-mono text-blue-200">
          Drop CSV, XLSX, or PDF files to attach/import
        </div>
      ) : null}

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
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => { void handleClearMessages() }}
            disabled={isStreaming || !canClearChat}
            className="rounded border border-red-500/40 bg-red-500/10 px-2 py-1 font-mono text-[11px] text-red-200 transition-colors hover:bg-red-500/20 disabled:cursor-default disabled:opacity-50"
            title={isStreaming ? 'Stop streaming before clearing chat' : 'Clear current chat session'}
          >
            Clear chat
          </button>
          <button
            type="button"
            onClick={openFilePicker}
            className="rounded border border-blue-500/40 bg-blue-500/10 px-2 py-1 font-mono text-[11px] text-blue-200 transition-colors hover:bg-blue-500/20"
            title="Attach CSV, XLSX, or PDF files"
          >
            Attach file
          </button>
          {isStreaming && (
            <button
              type="button"
              onClick={handleCancelStream}
              className="rounded border border-red-500/40 bg-red-500/10 px-2 py-1 font-mono text-[11px] text-red-300 transition-colors hover:bg-red-500/20"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4 pb-4">
          {(latestIngest || takeaways || attached.attached.length > 0) ? (
            <div className="space-y-3 rounded-lg border border-border/60 bg-black/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs font-mono text-muted-foreground">
                  Attached sources: {attached.attached.length}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSourcesOpen(true)}
                >
                  Recent sources
                </Button>
              </div>
              {watchlistNotice ? (
                <div
                  className={watchlistNotice.tone === 'error'
                    ? 'text-xs text-red-300'
                    : 'text-xs text-emerald-300'}
                >
                  {watchlistNotice.text}
                </div>
              ) : null}
              {latestIngest ? (
                <IngestSummaryCard
                  summary={latestIngest}
                  isAttached={attached.attached.some((source) => source.sourceId === latestIngest.sourceId)}
                  onAttach={(sourceId) => {
                    attached.attach({
                      sourceId,
                      sourceKind: latestIngest.sourceKind,
                      title: latestIngest.title,
                    })
                  }}
                  onDetach={(sourceId) => {
                    attached.detach(sourceId)
                  }}
                  onAddTicker={(ticker) => void addTickerToWatchlist(ticker)}
                />
              ) : null}
              {takeaways ? (
                <TakeawaysPanel
                  payload={takeaways}
                  onAddTicker={(input) => void addTickerToWatchlist(input.ticker, input.commentary)}
                  onJumpToCitation={openCitation}
                />
              ) : null}
            </div>
          ) : null}
          {messages.map((msg, index) => {
            const parentMessage = msg.role === 'assistant'
              ? [...messages.slice(0, index)].reverse().find((item) => item.role === 'user') ?? null
              : null
            const parentPrompt = parentMessage?.content ?? null
            return (
              <div key={msg.id} className="space-y-1">
                <TerminalMessage
                  message={msg}
                  showSources={preferences.showSources}
                  onConfirmAction={handleConfirmAction}
                  onCancelAction={handleCancelAction}
                />
                {msg.role === 'assistant' && (
                  <MessageClaimVerification
                    message={msg}
                    sessionId={sessionId}
                    parentMessageId={parentMessage?.id ?? null}
                    parentPrompt={parentPrompt}
                    ticker={activeTicker || null}
                    apiKey={apiKey}
                  >
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
                  </MessageClaimVerification>
                )}
              </div>
            )
          })}
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
                  ...streamingMetadata,
                  metadata: {
                    ...(streamingMetadata.metadata || {}),
                    latencyMs: streamingLatencyMs,
                  },
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

      <SourcesDrawer
        open={sourcesOpen}
        apiKey={apiKey}
        onClose={() => setSourcesOpen(false)}
        onReattach={({ sourceId, title }) => {
          attached.attach({ sourceId, sourceKind: 'ephemeral', title })
          setSourcesOpen(false)
        }}
      />

      <TerminalInput
        onSend={handleSend}
        disabled={isStreaming}
        onClear={handleClearMessages}
      />
    </div>
  )
}
