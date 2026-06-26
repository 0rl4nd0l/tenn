import { beforeEach, describe, expect, it, vi } from 'vitest'

type SSEOptions = Record<string, unknown>

const state = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  sseInstances: [] as Array<{ url: string; options: SSEOptions }>,
}))

class MockSSE {
  url: string
  options: SSEOptions

  constructor(url: string, options: SSEOptions) {
    this.url = url
    this.options = options
    state.sseInstances.push(this)
  }

  addEventListener = vi.fn()
  stream = vi.fn()
  close = vi.fn()
}

vi.mock('./api-client', () => ({
  apiFetch: state.apiFetch,
}))

vi.mock('sse.js', () => ({
  SSE: MockSSE,
}))

async function loadClient(apiKey: string | undefined = 'ops-secret') {
  vi.resetModules()
  state.apiFetch.mockReset()
  state.apiFetch.mockResolvedValue({ items: [], total: 0 })
  state.sseInstances.length = 0
  if (apiKey) {
    process.env.NEXT_PUBLIC_API_KEY = apiKey
  } else {
    delete process.env.NEXT_PUBLIC_API_KEY
  }
  return import('./ops-api-client')
}

describe('ops-api-client', () => {
  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_KEY
  })

  it('sends the configured local API key on ops job-state reads', async () => {
    const client = await loadClient('ops-secret')

    await client.listOpsJobs({ status: 'running', limit: 10 })
    await client.listActiveOpsJobs()
    await client.getOpsJob('job-1')
    await client.getOpsJobEvents('job-1', 25)
    await client.getOpsJobArtifacts('job-1')

    const headers = { 'X-API-Key': 'ops-secret' }
    expect(state.apiFetch).toHaveBeenNthCalledWith(
      1,
      '/api/ops/jobs?status=running&limit=10',
      { headers },
    )
    expect(state.apiFetch).toHaveBeenNthCalledWith(
      2,
      '/api/ops/jobs/active',
      { headers },
    )
    expect(state.apiFetch).toHaveBeenNthCalledWith(
      3,
      '/api/ops/jobs/job-1',
      { headers },
    )
    expect(state.apiFetch).toHaveBeenNthCalledWith(
      4,
      '/api/ops/jobs/job-1/events?limit=25',
      { headers },
    )
    expect(state.apiFetch).toHaveBeenNthCalledWith(
      5,
      '/api/ops/jobs/job-1/artifacts',
      { headers },
    )
  })

  it('does not send an empty API-key header when no key is configured', async () => {
    const client = await loadClient(undefined)

    await client.listActiveOpsJobs()

    expect(state.apiFetch).toHaveBeenCalledWith(
      '/api/ops/jobs/active',
      { headers: {} },
    )
  })

  it('builds an authenticated SSE stream without placing key material in the URL', async () => {
    const client = await loadClient('ops-secret')

    const source = client.createOpsJobStream('job 1')

    const instance = state.sseInstances.at(0)
    expect(source).toBe(instance)
    expect(instance?.url).toBe('/api/ops/stream?job_id=job%201')
    expect(instance?.url).not.toContain('ops-secret')
    expect(instance?.options).toEqual({
      headers: { 'X-API-Key': 'ops-secret' },
      start: false,
    })
  })
})
