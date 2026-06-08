import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CockpitStatusBar } from './cockpit-status-bar'
import { useCockpitStore } from '@/lib/cockpit-store'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

function renderStatusBar({
  backendHealthy = true,
  backendError = null,
}: {
  backendHealthy?: boolean
  backendError?: string | null
} = {}) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={client}>
      <CockpitStatusBar
        backendHealthy={backendHealthy}
        backendLastHealthyAt={new Date('2026-05-07T00:00:00Z')}
        backendError={backendError}
      />
    </QueryClientProvider>,
  )
}

describe('CockpitStatusBar operator detail gate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useCockpitStore.setState({
      apiDefaultEnabled: false,
      activeSource: 'local',
      sessionStats: {
        totalCostUsd: 0.1234,
        lastLatencyMs: 42,
        activeModel: 'model:qwen3.5-35b-a3b-apex',
      },
    })
  })

  it('summarizes runtime state without exposing model, token, temperature, or profile internals', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          llm_model: 'model:qwen3.5-35b-a3b-apex',
          max_tokens: 8192,
          temperature: 0.67,
          profile: 'ops',
          anthropic_key_configured: true,
          extraction_active: false,
        }),
      })),
    )

    renderStatusBar()

    expect(await screen.findByText('Runtime: ready')).toBeInTheDocument()
    expect(screen.getByText('Cloud route: available')).toBeInTheDocument()
    expect(screen.getByText('Extract: idle')).toBeInTheDocument()

    expect(screen.queryByText(/qwen3\.5-35b-a3b-apex/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/max 8192/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/temp 0\.67/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/profile: ops/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Selected:/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Active:/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Source:/i)).not.toBeInTheDocument()
  })

  it('sanitizes backend errors in global chrome', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 500,
        json: async () => ({}),
      })),
    )

    renderStatusBar({
      backendHealthy: false,
      backendError: 'Command failed: nvidia-smi --query-gpu=name',
    })

    expect(await screen.findByText('Runtime: backend down')).toBeInTheDocument()
    expect(screen.getByText('backend critical: unavailable; open Operations for details')).toBeInTheDocument()
    expect(screen.queryByText(/nvidia-smi/i)).not.toBeInTheDocument()
  })
})
