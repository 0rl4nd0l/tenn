import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useCockpitStore } from '@/lib/cockpit-store'
import {
  deleteChatSessionRemote,
  getActionJob,
  getChatSessionMessages,
  previewAction,
  restartBackend,
  sendChatMessage,
  startActionJob,
  streamChat,
} from '@/lib/api-client'

import { ChatScreen } from './chat-screen'

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/api-client', () => ({
  deleteChatSessionRemote: vi.fn(async () => undefined),
  getActionJob: vi.fn(),
  getChatSessionMessages: vi.fn(),
  previewAction: vi.fn(),
  restartBackend: vi.fn(async () => ({ message: 'ok' })),
  sendChatMessage: vi.fn(),
  startActionJob: vi.fn(),
  streamChat: vi.fn(),
  submitResponseFeedback: vi.fn(async () => ({
    ok: true,
    feedback_id: 'fb-1',
    created_at: '2026-06-03T05:00:00Z',
    storage_path: 'reports/feedback/fb-1.json',
  })),
  verifyClaims: vi.fn(async () => ({
    ok: true,
    checked_at: '2026-06-03T05:00:00Z',
    evidence_scope: 'message',
    evidence_count: 0,
    verdicts: [],
  })),
}))

vi.mock('@/lib/chat-session-store', () => ({
  deleteChatSession: vi.fn(),
  loadChatSession: vi.fn(() => ({ messages: [] })),
  saveChatSession: vi.fn(),
}))

function renderChatScreen() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={client}>
      <ChatScreen />
    </QueryClientProvider>,
  )
}

describe('ChatScreen suggested actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    window.localStorage.setItem('cockpit.apiKey', 'test-key')

    useCockpitStore.setState({
      activeTicker: '',
      sessionId: 'session-1',
      chatModel: 'model:test',
      chatCompletionActive: false,
      apiDefaultEnabled: false,
      activeSource: 'unknown',
      preferences: {
        webSearchEnabled: true,
        ragEnabled: true,
        dbDiagnosticsEnabled: false,
        showSources: true,
        theme: 'dark',
        marketplaceHomeLocation: '',
        marketplacePreferCloudRouting: false,
        chatRoutingPolicyOverride: 'config_default',
        chatRuntimeTarget: 'local',
        iphoneScale: false,
      },
      sessionStats: {
        totalCostUsd: 0,
        lastLatencyMs: 0,
        activeModel: 'local-model',
      },
      isBackendHealthy: true,
      backendError: null,
    })

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          llm_model: 'local-model',
          extraction_active: false,
          extraction_active_runs: [],
          anthropic_key_configured: false,
        }),
      })),
    )

    vi.mocked(streamChat).mockImplementation(() => {
      throw new Error('streamChat should not be called in this test')
    })
    vi.mocked(sendChatMessage).mockImplementation(async () => {
      throw new Error('sendChatMessage should not be called in this test')
    })
    vi.mocked(restartBackend).mockResolvedValue({ ok: true, message: 'ok' })
    vi.mocked(deleteChatSessionRemote).mockResolvedValue({ ok: true, deleted_count: 0 })
  })

  it('routes metric-extraction suggestions through preview, confirmation, and progress logging', async () => {
    const user = userEvent.setup()

    vi.mocked(getChatSessionMessages).mockResolvedValue([
      {
        id: 1,
        role: 'assistant',
        content: 'I can discuss filings, but financial rows unavailable.',
        created_at: '2026-06-03T05:00:00Z',
        routing_metadata: {
          primary_ticker: 'MIN',
          missing_categories_after_recovery: ['financials'],
          sufficient_for_analysis: false,
        },
        sources: [],
      },
    ] as never)

    vi.mocked(previewAction).mockResolvedValue({
      action_id: 'metric_extraction',
      command: ['python', 'scripts/rebuild_ticker_financials_from_docs.py', '--ticker', 'MIN'],
      summary: 'Extract ticker financial metrics for MIN.',
      estimated_impact: 'Reads source documents and writes extracted metric outputs.',
      timeout_seconds: 10800,
      guard_message: 'Requires confirmation.',
    })

    vi.mocked(startActionJob).mockResolvedValue({
      action_id: 'metric_extraction',
      job_id: 'job-1',
      status: 'queued',
      queued: true,
    })

    vi.mocked(getActionJob).mockResolvedValue({
      job_id: 'job-1',
      action_id: 'metric_extraction',
      status: 'completed',
      progress_stage: 'done',
      progress_pct: 100,
      result: 'Metric extraction completed.',
    })

    renderChatScreen()

    const actionButton = await screen.findByRole('button', { name: 'Run metric extraction' })
    await user.click(actionButton)

    expect(previewAction).toHaveBeenCalledWith({
      actionId: 'metric_extraction',
      args: { ticker: 'MIN' },
    })
    expect(await screen.findByRole('button', { name: 'Confirm' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(startActionJob).toHaveBeenCalledWith({
      actionId: 'metric_extraction',
      args: { ticker: 'MIN' },
      sessionId: 'session-1',
    })

    await waitFor(() => {
      expect(screen.getByText(/status: queued/i)).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(getActionJob).toHaveBeenCalledWith('job-1')
    })
    await waitFor(() => {
      expect(screen.getByText(/Metric extraction completed\./i)).toBeInTheDocument()
    })
  }, 10000)
})
