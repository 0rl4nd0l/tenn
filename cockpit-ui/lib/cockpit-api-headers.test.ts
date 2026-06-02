import { afterEach, describe, expect, it, vi } from 'vitest'

describe('Cockpit API headers', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_KEY
    window.localStorage.clear()
    vi.resetModules()
  })

  it('adds the configured browser API key', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    const { buildCockpitApiHeaders } = await import('./cockpit-api-headers')

    expect(buildCockpitApiHeaders()).toEqual({ 'X-API-Key': 'operator-key' })
  })

  it('prefers the operator key stored by the browser UI', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'env-key'
    window.localStorage.setItem('cockpit.apiKey', 'stored-key')
    const { buildCockpitApiHeaders } = await import('./cockpit-api-headers')

    expect(buildCockpitApiHeaders()).toEqual({ 'X-API-Key': 'stored-key' })
  })

  it('preserves existing headers when adding the key', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    const { buildCockpitApiHeaders } = await import('./cockpit-api-headers')

    expect(buildCockpitApiHeaders({ 'Content-Type': 'application/json' })).toEqual({
      'Content-Type': 'application/json',
      'X-API-Key': 'operator-key',
    })
  })

  it('preserves tuple and Headers inputs', async () => {
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key'
    const { buildCockpitApiHeaders } = await import('./cockpit-api-headers')

    expect(buildCockpitApiHeaders([['Accept', 'application/json']])).toEqual({
      Accept: 'application/json',
      'X-API-Key': 'operator-key',
    })
    expect(buildCockpitApiHeaders(new Headers({ Accept: 'application/json' }))).toEqual({
      accept: 'application/json',
      'X-API-Key': 'operator-key',
    })
  })

  it('does not add an empty API key', async () => {
    const { buildCockpitApiHeaders } = await import('./cockpit-api-headers')

    expect(buildCockpitApiHeaders()).toEqual({})
  })
})
