import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BootScreen } from '@/components/cockpit/boot/boot-screen'

const pushMock = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

describe('BootScreen health contract', () => {
  beforeEach(() => {
    pushMock.mockReset()
  })

  it('uses the Cockpit health BFF instead of browser-local runtime probes', async () => {
    const requestedUrls: string[] = []
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      requestedUrls.push(String(input))
      return {
        ok: true,
        status: 200,
        json: async () => ({
          status: 'healthy',
          services: [
            { name: 'backend', status: 'healthy', endpoint: 'http://localhost:8000', response_time_ms: 3 },
            { name: 'llamacpp', status: 'healthy', endpoint: 'http://localhost:8001', response_time_ms: 9 },
            { name: 'ollama', status: 'healthy', endpoint: 'http://localhost:11434', response_time_ms: 11 },
            { name: 'qdrant', status: 'healthy', endpoint: 'http://localhost:6333', response_time_ms: 7 },
            { name: 'redis', status: 'healthy', endpoint: 'redis://localhost:6379/0', response_time_ms: 2 },
            { name: 'gpu', status: 'healthy', response_time_ms: 4 },
            { name: 'host', status: 'healthy', response_time_ms: 1 },
          ],
        }),
      }
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<BootScreen />)

    await screen.findByText('Service check complete')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(requestedUrls).toEqual(['/api/cockpit/health'])
    const browserLocalRuntimeProbe = /^http:\/\/(localhost|127\.0\.0\.1):(8001|11434|6333|6379)\b/
    expect(requestedUrls.some((url) => browserLocalRuntimeProbe.test(url))).toBe(false)

    expect(screen.getByText('llama.cpp')).toBeInTheDocument()
    expect(screen.getByText('Ollama Embeddings')).toBeInTheDocument()
    expect(screen.getByText('Qdrant')).toBeInTheDocument()
    expect(screen.getByText('Redis')).toBeInTheDocument()
    expect(screen.getByText('GPU')).toBeInTheDocument()
    expect(screen.getByText('Host')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.queryByText(/Direct health checks/i)).not.toBeInTheDocument()
  })

  it('keeps BFF-unverified services unknown instead of probing from the browser', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'healthy',
        services: [
          { name: 'backend', status: 'healthy' },
          { name: 'llamacpp', status: 'healthy' },
          { name: 'ollama', status: 'healthy' },
        ],
      }),
    }))

    vi.stubGlobal('fetch', fetchMock)

    render(<BootScreen />)

    await screen.findByText('Service check complete')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    await waitFor(() => {
      expect(screen.getAllByText('Not reported by health BFF').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getByText(/Some statuses are unknown because the health BFF did not verify them/i)).toBeInTheDocument()
  })
})
