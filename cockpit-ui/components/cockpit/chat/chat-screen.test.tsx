import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useCockpitStore } from '@/lib/cockpit-store'
import {
  deleteChatSessionRemote,
  fetchChatReadiness,
  getChatSessionMessages,
  restartBackend,
  sendChatMessage,
  streamChat,
} from '@/lib/api-client'

import { ChatScreen } from './chat-screen'

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/api-client', () => ({
  deleteChatSessionRemote: vi.fn(async () => undefined),
  fetchChatReadiness: vi.fn(),
  getActionJob: vi.fn(),
  getChatSessionMessages: vi.fn(),
  restartBackend: vi.fn(async () => ({ message: 'ok' })),
  sendChatMessage: vi.fn(),
  startActionJob: vi.fn(),
  streamChat: vi.fn(),
  withApiKey: vi.fn(() => ({ 'X-API-Key': 'test-key' })),
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

describe('ChatScreen readiness', () => {
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
    vi.mocked(getChatSessionMessages).mockResolvedValue([])
    vi.mocked(fetchChatReadiness).mockResolvedValue({
      schema_version: 1,
      answer_ready: true,
      normal_analysis_allowed: true,
      capabilities: {
        financial_fact: {
          id: 'financial_fact',
          label: 'Financial facts',
          status: 'READY',
          ready: true,
          blockers: [],
        },
        filing_document_summary: {
          id: 'filing_document_summary',
          label: 'Filing and document summaries',
          status: 'READY',
          ready: true,
          blockers: [],
        },
        local_news_rag: {
          id: 'local_news_rag',
          label: 'Local news and RAG',
          status: 'READY',
          ready: true,
          blockers: [],
        },
        model_route_runtime: {
          id: 'model_route_runtime',
          label: 'Model route and runtime',
          status: 'READY',
          ready: true,
          blockers: [],
        },
      },
      summary: {
        primary_blockers: [],
        safe_activation_actions: [],
      },
    })
  })

  it('renders capability blockers when normal analysis is not answer-ready', async () => {
    vi.mocked(fetchChatReadiness).mockResolvedValue({
      schema_version: 1,
      ticker: 'BHP',
      answer_ready: false,
      normal_analysis_allowed: false,
      capabilities: {
        financial_fact: {
          id: 'financial_fact',
          label: 'Financial facts',
          status: 'DATA_MISSING',
          ready: false,
          blockers: ['asx_periodic_financials table unavailable'],
        },
        filing_document_summary: {
          id: 'filing_document_summary',
          label: 'Filing and document summaries',
          status: 'DATA_MISSING',
          ready: false,
          blockers: ['no filings/documents for requested ticker'],
        },
        local_news_rag: {
          id: 'local_news_rag',
          label: 'Local news and RAG',
          status: 'DATA_MISSING',
          ready: false,
          blockers: ['ENABLE_QDRANT=false'],
        },
        model_route_runtime: {
          id: 'model_route_runtime',
          label: 'Model route and runtime',
          status: 'DEGRADED',
          ready: false,
          blockers: ['connection refused'],
        },
      },
      summary: {
        primary_blockers: ['financial_fact', 'filing_document_summary'],
        safe_activation_actions: [
          'Run reviewed metric extraction for the ticker before numeric financial questions.',
        ],
      },
    })

    renderChatScreen()

    expect(await screen.findByText('Normal analysis blocked')).toBeInTheDocument()
    expect(screen.getByText('Financial facts')).toBeInTheDocument()
    expect(screen.getByText('asx_periodic_financials table unavailable')).toBeInTheDocument()
    expect(screen.getByText('Local news and RAG')).toBeInTheDocument()
    expect(screen.getByText('ENABLE_QDRANT=false')).toBeInTheDocument()
  })

  it('blocks normal chat submission when readiness is not answer-ready', async () => {
    vi.mocked(fetchChatReadiness).mockResolvedValue({
      schema_version: 1,
      ticker: 'BHP',
      answer_ready: false,
      normal_analysis_allowed: false,
      capabilities: {
        financial_fact: {
          id: 'financial_fact',
          label: 'Financial facts',
          status: 'DATA_MISSING',
          ready: false,
          blockers: ['asx_periodic_financials table unavailable'],
        },
        model_route_runtime: {
          id: 'model_route_runtime',
          label: 'Model route and runtime',
          status: 'READY',
          ready: true,
          blockers: [],
        },
      },
      summary: {
        primary_blockers: ['financial_fact'],
        safe_activation_actions: [
          'Run reviewed metric extraction for the ticker before numeric financial questions.',
        ],
      },
    })
    const user = userEvent.setup()

    renderChatScreen()

    expect(await screen.findByText('Normal analysis blocked')).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('Enter command or query...'), 'What was BHP revenue?{enter}')

    expect(await screen.findByText(/Normal analysis is blocked until required answer capabilities are ready/i)).toBeInTheDocument()
    expect(screen.getByText(/Financial facts: asx_periodic_financials table unavailable/i)).toBeInTheDocument()
    expect(streamChat).not.toHaveBeenCalled()
    expect(sendChatMessage).not.toHaveBeenCalled()
  })
})
