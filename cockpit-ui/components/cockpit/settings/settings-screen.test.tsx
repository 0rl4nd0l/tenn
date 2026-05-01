import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SettingsScreen } from './settings-screen'
import { useCockpitStore } from '@/lib/cockpit-store'

describe('SettingsScreen', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
    const elementPrototype = Element.prototype as Element & {
      hasPointerCapture?: (pointerId: number) => boolean
      setPointerCapture?: (pointerId: number) => void
      releasePointerCapture?: (pointerId: number) => void
    }
    elementPrototype.hasPointerCapture ??= () => false
    elementPrototype.setPointerCapture ??= () => undefined
    elementPrototype.releasePointerCapture ??= () => undefined
    useCockpitStore.setState((state) => ({
      ...state,
      preferences: {
        ...state.preferences,
        marketplaceHomeLocation: '',
        marketplacePreferCloudRouting: false,
        chatRoutingPolicyOverride: 'config_default',
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

  it('lets the user select a Cockpit chat route override', async () => {
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
            routing_policy: 'api_preferred',
            routing_policy_override: 'config_default',
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
      expect(screen.getByText(/chat route override/i)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('combobox', { name: /chat route override/i }))
    await userEvent.click(await screen.findByRole('option', { name: /local only/i }))

    expect(useCockpitStore.getState().preferences.chatRoutingPolicyOverride).toBe('local_only')
  })
})
