import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CockpitSidebar } from './cockpit-sidebar'
import { SidebarProvider } from '@/components/ui/sidebar'
import { useCockpitStore } from '@/lib/cockpit-store'
import type { ServiceHealth } from '@/lib/cockpit-types'
import {
  deleteChatSessionRemote,
  listChatSessions,
} from '@/lib/api-client'
import { deleteChatSession } from '@/lib/chat-session-store'

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

function renderSidebar({ gpuHealth = null }: { gpuHealth?: ServiceHealth | null } = {}) {
  return render(
    <SidebarProvider>
      <CockpitSidebar
        backendHealthy
        backendLastHealthyAt={new Date('2026-05-07T00:00:00Z')}
        backendError={null}
        gpuHealth={gpuHealth}
        hostHealth={null}
        sessionCost={0}
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

  it('does not summarize degraded GPU telemetry as a confirmed idle process list', async () => {
    renderSidebar({
      gpuHealth: {
        name: 'gpu',
        status: 'degraded',
        error: 'nvidia-smi query failed',
        details: {
          gpus: [],
          processes: [],
        },
      },
    })

    expect(await screen.findByText('GPU process telemetry unavailable')).toBeInTheDocument()
    expect(screen.queryByText('No active GPU compute processes')).not.toBeInTheDocument()
  })
})
