import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MemoryScreen } from './memory-screen'

vi.mock('next/navigation', () => ({
  usePathname: () => '/memory',
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/cockpit-store', () => ({
  useCockpitStore: () => ({
    activeTicker: 'BHP',
    setActiveTicker: vi.fn(),
  }),
}))

const MEMORY_WRITE_CONFIRMATION = 'reviewed-memory-write'
const MEMORY_WRITE_INTENT_HEADER = 'X-Cockpit-Memory-Write-Intent'

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function emptyMemoryPayload() {
  return {
    summary: {},
    memory_levels: [],
    company_memory: {
      entries: [],
      change_log: [],
    },
    market_memory: {
      sector_items: [],
      macro_items: [],
    },
    user_thesis_memory: {
      entries: [],
      proposals: [],
    },
  }
}

function mockMemoryFetch() {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    if (init?.method === 'POST') {
      return Promise.resolve(jsonResponse({ ok: true }))
    }
    if (path.startsWith('/api/cockpit/memory')) {
      return Promise.resolve(jsonResponse(emptyMemoryPayload()))
    }
    return Promise.resolve(jsonResponse({ items: [] }))
  })
}

describe('MemoryScreen write confirmation', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('does not submit a Memory Workbench write when the visible confirmation is cancelled', async () => {
    const fetchMock = mockMemoryFetch()
    vi.stubGlobal('fetch', fetchMock)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(<MemoryScreen apiKey="test-key" />)

    await screen.findByText('Loaded full persistent memory index.')
    await userEvent.type(screen.getByPlaceholderText('Enter memory statement...'), 'durable company note')
    await userEvent.click(screen.getByRole('button', { name: 'Add Entry' }))

    expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining('Confirm add memory entry'))
    await waitFor(() => expect(screen.getByText('Memory write cancelled.')).toBeInTheDocument())
    expect(fetchMock.mock.calls.some((call) => call[0] === '/api/cockpit/memory/company/add')).toBe(false)
  })

  it('submits company writes with confirmation and route-specific intent evidence', async () => {
    const fetchMock = mockMemoryFetch()
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(<MemoryScreen apiKey="test-key" />)

    await screen.findByText('Loaded full persistent memory index.')
    await userEvent.type(screen.getByPlaceholderText('Enter memory statement...'), 'durable company note')
    await userEvent.click(screen.getByRole('button', { name: 'Add Entry' }))

    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => call[0] === '/api/cockpit/memory/company/add')).toBe(true)
    })
    const mutationCall = fetchMock.mock.calls.find((call) => call[0] === '/api/cockpit/memory/company/add')
    expect(mutationCall).toBeDefined()
    const init = mutationCall?.[1] as RequestInit
    expect(init.headers).toMatchObject({
      'Content-Type': 'application/json',
      'X-API-Key': 'test-key',
      [MEMORY_WRITE_INTENT_HEADER]: 'company-memory-add',
    })
    expect(JSON.parse(String(init.body))).toMatchObject({
      ticker: 'BHP',
      type: 'observed_fact',
      statement: 'durable company note',
      note: 'web-memory-tab',
      intent: 'company-memory-add',
      confirmation: MEMORY_WRITE_CONFIRMATION,
    })
  })
})
