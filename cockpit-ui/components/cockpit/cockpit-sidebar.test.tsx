import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CockpitSidebar } from './cockpit-sidebar'
import { SidebarProvider } from '@/components/ui/sidebar'
import { useCockpitStore } from '@/lib/cockpit-store'
import {
  deleteChatSessionRemote,
  listChatSessions,
} from '@/lib/api-client'
import { deleteChatSession } from '@/lib/chat-session-store'
import type { ServiceHealth } from '@/lib/cockpit-types'

vi.mock('next/navigation', () => ({
  usePathname: () => '/full-chat',
}))

vi.mock('@/lib/api-client', () => ({
  createChatSessionRemote: vi.fn(async () => undefined),
  deleteChatSessionRemote: vi.fn(async () => undefined),
  listChatSessions: vi.fn(),
}))

vi.mock('@/lib/chat-session-store', () => ({
  createChatSessionId: vi.fn(() => 'new-session'),
  deleteChatSession: vi.fn(),
  loadAllChatSessions: vi.fn(() => []),
}))

type SidebarProps = Parameters<typeof CockpitSidebar>[0]

function renderSidebar(overrides: Partial<SidebarProps> = {}) {
  return render(
    <SidebarProvider>
      <CockpitSidebar
        backendHealthy
        backendLastHealthyAt={new Date('2026-05-07T00:00:00Z')}
        backendError={null}
        gpuHealth={null}
        hostHealth={null}
        sessionCost={0}
        {...overrides}
      />
    </SidebarProvider>,
  )
}

describe('CockpitSidebar chat sessions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({}),
      })),
    )
    vi.mocked(listChatSessions).mockResolvedValue([
      {
        session_id: 'session-alpha',
        title: 'Session Alpha',
        updated_at: '2026-05-07T00:00:00Z',
        message_count: 3,
      },
    ])
    useCockpitStore.setState({
      sessionId: 'active-session',
      apiDefaultEnabled: false,
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
        activeModel: 'unknown',
      },
    })
  })

  it('renders delete as a sibling action instead of a nested button', async () => {
    const user = userEvent.setup()
    renderSidebar()

    const sessionButton = await screen.findByRole('button', {
      name: 'Session Alpha',
    })
    const deleteButton = screen.getByRole('button', {
      name: 'Delete chat session: Session Alpha',
    })

    expect(sessionButton).not.toContainElement(deleteButton)
    expect(sessionButton.querySelector('button')).toBeNull()

    await user.click(deleteButton)

    await waitFor(() => {
      expect(deleteChatSessionRemote).toHaveBeenCalledWith('session-alpha')
    })
    expect(deleteChatSession).toHaveBeenCalledWith('session-alpha')
    expect(useCockpitStore.getState().sessionId).toBe('active-session')
  })

  it('keeps raw host, GPU, and config internals out of normal sidebar chrome', async () => {
    const rawGpuError = 'Command failed: nvidia-smi --query-gpu=name,temperature.gpu'
    const rawHostCommand = '/usr/bin/top -b -n 1'
    const hostHealth: ServiceHealth = {
      name: 'host',
      status: 'down',
      error: rawHostCommand,
      details: {},
    }
    const gpuHealth: ServiceHealth = {
      name: 'gpu',
      status: 'unknown',
      error: rawGpuError,
      details: {
        processes: [
          {
            pid: 1234,
            command: 'python local-model-worker.py --model qwen3.5-35b-a3b-apex',
          },
        ],
      },
    }

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          llm_model: 'model:qwen3.5-35b-a3b-apex',
          max_tokens: 8192,
          temperature: 0.67,
          routing_policy: 'api_preferred',
          profile: 'ops',
        }),
      })),
    )

    renderSidebar({ hostHealth, gpuHealth })

    expect(await screen.findByTestId('cockpit-config-summary')).toHaveTextContent('Runtime Readiness')
    expect(screen.getByText('Host telemetry unavailable. Open details for diagnostics.')).toBeInTheDocument()
    expect(screen.getByText('GPU telemetry pending. Open details for diagnostics.')).toBeInTheDocument()
    expect(screen.getByText('Open operator settings')).toBeInTheDocument()

    expect(screen.queryByText(/nvidia-smi/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/local-model-worker/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/qwen3\.5-35b-a3b-apex/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/max_tokens/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/temp/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/api_preferred/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/profile: ops/i)).not.toBeInTheDocument()
  })
})
