import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MarketplaceAssistant } from './marketplace-assistant'
import { useCockpitStore } from '@/lib/cockpit-store'

describe('MarketplaceAssistant', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    window.sessionStorage.clear()
    useCockpitStore.setState((state) => ({
      ...state,
      activeSource: 'local',
      apiDefaultEnabled: false,
      chatModel: 'model:qwen-test',
      preferences: {
        ...state.preferences,
        webSearchEnabled: true,
        marketplaceHomeLocation: 'Melbourne',
        marketplacePreferCloudRouting: false,
      },
    }))
  })

  it('seeds the saved location into the greeting and can create then run a mission', async () => {
    const onMarketplaceStateChange = vi.fn().mockResolvedValue(undefined)
    const onScanQueued = vi.fn()

    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content: {
          answer: JSON.stringify({
            assistant_message: 'I have enough to draft this. Create it now or create and run it.',
            draft: {
              name: 'Used GPU',
              brief: 'Find an RTX 3090 under $900 in Melbourne with no repair history.',
              hardFilters: {
                includeKeywords: ['RTX 3090'],
                forbiddenTerms: ['repair', 'artifacting'],
                priceMax: 900,
              },
            },
            missing_fields: [],
            ready_to_create: true,
            suggested_action: 'confirm_create_and_run',
          }),
          model: 'model:qwen-test',
          source: 'local',
        },
      }),
    }).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        mission_id: 'mp-1',
        name: 'Used GPU',
      }),
    }).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        job_id: 'job-77',
      }),
    }).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        mission_id: 'mp-1',
        name: 'Used GPU',
        status: 'active',
      }),
    })

    vi.stubGlobal('fetch', fetchMock)

    render(
      <MarketplaceAssistant
        apiKey="secret"
        browserHealth={{
          status: 'ready',
          cdp_url: 'http://127.0.0.1:9222',
          browser_family: 'chrome',
          profile_path: '/tmp/profile',
          challenge_detected: false,
          last_checked_at: '2026-04-20T00:00:00Z',
        }}
        onMarketplaceStateChange={onMarketplaceStateChange}
        onScanQueued={onScanQueued}
      />,
    )

    expect(
      screen.getByText(/i know your default marketplace location is melbourne/i),
    ).toBeInTheDocument()

    const prompt = screen.getByRole('textbox', { name: /marketplace assistant prompt/i })
    await userEvent.type(prompt, 'I want a used RTX 3090 under $900 with no repair history.')
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    await waitFor(() => {
      expect(screen.getByText(/i have enough to draft this/i)).toBeInTheDocument()
    })

    const chatRequest = fetchMock.mock.calls[0]
    expect(chatRequest[0]).toBe('/api/cockpit/chat')
    expect(JSON.parse(String(chatRequest[1]?.body))).toEqual(
      expect.objectContaining({
        session_id: expect.any(String),
        model: 'model:qwen-test',
        mode: 'marketplace',
        web_search: true,
        rag: false,
        db_diagnostics: false,
      }),
    )
    expect(JSON.parse(String(chatRequest[1]?.body)).message).toContain('/local')
    expect(JSON.parse(String(chatRequest[1]?.body)).message).toContain('Saved home location: Melbourne')

    expect(screen.getByText(/ready to create/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /save and run now/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(4)
    })

    expect(fetchMock.mock.calls[1][0]).toBe('/api/cockpit/marketplace/missions')
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual(
      expect.objectContaining({
        name: 'Used GPU',
        status: 'paused',
      }),
    )
    expect(fetchMock.mock.calls[2][0]).toBe('/api/cockpit/marketplace/scans')
    expect(fetchMock.mock.calls[3][0]).toBe('/api/cockpit/marketplace/missions/mp-1')
    expect(JSON.parse(String(fetchMock.mock.calls[3][1]?.body))).toEqual({ status: 'active' })
    expect(onScanQueued).toHaveBeenCalledWith('job-77')
    expect(onMarketplaceStateChange).toHaveBeenCalled()
    expect(screen.getByText(/created mission and queued scan job-77/i)).toBeInTheDocument()
  })

  it('pins Marketplace assistant turns to cloud when the Marketplace cloud preference is enabled', async () => {
    useCockpitStore.setState((state) => ({
      ...state,
      activeSource: 'local',
      apiDefaultEnabled: false,
      chatModel: 'model:qwen-test',
      preferences: {
        ...state.preferences,
        webSearchEnabled: true,
        marketplaceHomeLocation: 'Melbourne',
        marketplacePreferCloudRouting: true,
      },
    }))

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        content: {
          answer: JSON.stringify({
            assistant_message: 'What budget do you have?',
            draft: {},
            missing_fields: ['budget'],
            ready_to_create: false,
            suggested_action: 'ask_followup',
          }),
          model: 'model:qwen-test',
          source: 'anthropic',
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MarketplaceAssistant
        apiKey="secret"
        browserHealth={null}
        onMarketplaceStateChange={vi.fn()}
      />,
    )

    await userEvent.type(
      screen.getByRole('textbox', { name: /marketplace assistant prompt/i }),
      'I want a used RTX 3090 in Victoria.',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    const chatRequest = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))
    expect(chatRequest.message).toContain('/cloud')
    expect(screen.getByText('Route: cloud')).toBeInTheDocument()
  })
})
