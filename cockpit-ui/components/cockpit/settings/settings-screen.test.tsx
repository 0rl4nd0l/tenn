import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SettingsScreen } from './settings-screen'
import { useCockpitStore } from '@/lib/cockpit-store'

describe('SettingsScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    useCockpitStore.setState((state) => ({
      ...state,
      preferences: {
        ...state.preferences,
        marketplaceHomeLocation: '',
        marketplacePreferCloudRouting: false,
      },
    }))
  })

  it('lets the user save a Marketplace home location in Cockpit preferences', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            llm_model: 'model:qwen-test',
            llm_endpoint: 'http://localhost:8001',
            routing_policy: 'local-first',
            backend_url: 'http://localhost:8000',
            profile: 'isolated',
            features: {
              web_search: true,
              rag: true,
              extraction: true,
            },
            python_version: '3.11.8',
            git_branch: 'main',
            data_root: '/data/financial-engine',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            groups: [],
          }),
        }),
    )

    const { container } = render(<SettingsScreen />)

    await waitFor(() => {
      expect(screen.getByText(/marketplace preferences/i)).toBeInTheDocument()
    })

    const row = screen.getByText(/home location \/ suburb/i).closest('div')
    const input = row?.querySelector('input') ?? container.querySelector('input')
    expect(input).toBeTruthy()

    await userEvent.type(input as HTMLInputElement, 'Melbourne')

    expect(useCockpitStore.getState().preferences.marketplaceHomeLocation).toBe('Melbourne')
  })

  it('lets the user save the Marketplace cloud-routing preference', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            llm_model: 'model:qwen-test',
            llm_endpoint: 'http://localhost:8001',
            routing_policy: 'local-first',
            backend_url: 'http://localhost:8000',
            profile: 'isolated',
            features: {
              web_search: true,
              rag: true,
              extraction: true,
            },
            python_version: '3.11.8',
            git_branch: 'main',
            data_root: '/data/financial-engine',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            groups: [],
          }),
        }),
    )

    render(<SettingsScreen />)

    await waitFor(() => {
      expect(screen.getByLabelText(/prefer cloud routing for marketplace assistant/i)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByLabelText(/prefer cloud routing for marketplace assistant/i))

    expect(useCockpitStore.getState().preferences.marketplacePreferCloudRouting).toBe(true)
  })
})
