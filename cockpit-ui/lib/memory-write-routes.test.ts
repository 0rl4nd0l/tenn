import { afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

import { POST as postCompanyAdd } from '@/app/api/cockpit/memory/company/add/route'
import { POST as postCompanyExpire } from '@/app/api/cockpit/memory/company/expire/route'
import { POST as postMarketAdd } from '@/app/api/cockpit/memory/market/add/route'
import { POST as postMarketExpire } from '@/app/api/cockpit/memory/market/expire/route'
import { POST as postThesisProposal } from '@/app/api/cockpit/memory/thesis/proposals/route'
import { POST as postThesisApply } from '@/app/api/cockpit/memory/thesis/proposals/[proposalId]/apply/route'
import { POST as postThesisConfirm } from '@/app/api/cockpit/memory/thesis/proposals/[proposalId]/confirm/route'
import { POST as postThesisReject } from '@/app/api/cockpit/memory/thesis/proposals/[proposalId]/reject/route'

const MEMORY_WRITE_CONFIRMATION = 'reviewed-memory-write'
const MEMORY_WRITE_INTENT_HEADER = 'X-Cockpit-Memory-Write-Intent'

type RouteCall = (request: NextRequest) => Promise<Response>

function memoryWriteRequest(
  path: string,
  body: Record<string, unknown>,
  intent: string,
  headerIntent = intent,
): NextRequest {
  return new NextRequest(`http://localhost${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'test-key',
      ...(headerIntent ? { [MEMORY_WRITE_INTENT_HEADER]: headerIntent } : {}),
    },
    body: JSON.stringify({
      ...body,
      intent,
      confirmation: MEMORY_WRITE_CONFIRMATION,
    }),
  })
}

function proposalContext(proposalId = 'proposal-1') {
  return { params: Promise.resolve({ proposalId }) }
}

describe('Memory Workbench write BFF guards', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('rejects missing route-specific intent before proxying to backend memory stores', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const response = await postCompanyAdd(
      memoryWriteRequest(
        '/api/cockpit/memory/company/add',
        { ticker: 'BHP', type: 'observed_fact', statement: 'durable note' },
        'company-memory-add',
        '',
      ),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'memory_write_intent_header_required',
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects incorrect body intent before proxying to backend memory stores', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const response = await postCompanyExpire(
      memoryWriteRequest(
        '/api/cockpit/memory/company/expire',
        { ticker: 'BHP', entry_id: 12, note: 'expire' },
        'company-memory-add',
        'company-memory-expire',
      ),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'memory_write_intent_body_required',
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('rejects market scope and intent mismatches before proxying to backend', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const response = await postMarketAdd(
      memoryWriteRequest(
        '/api/cockpit/memory/market/add',
        { scope: 'sector', ticker: 'BHP', type: 'sector_trend', statement: 'sector note' },
        'macro-memory-add',
      ),
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'memory_write_intent_header_required',
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('proxies every classified Memory Workbench write path with explicit intent evidence', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000'
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })),
    )
    vi.stubGlobal('fetch', fetchMock)

    const cases: Array<{
      name: string
      call: RouteCall
      path: string
      backendPath: string
      intent: string
      body: Record<string, unknown>
    }> = [
      {
        name: 'company add',
        call: postCompanyAdd,
        path: '/api/cockpit/memory/company/add',
        backendPath: '/api/context/memory/company/add',
        intent: 'company-memory-add',
        body: { ticker: 'BHP', type: 'observed_fact', statement: 'company note' },
      },
      {
        name: 'company expire',
        call: postCompanyExpire,
        path: '/api/cockpit/memory/company/expire',
        backendPath: '/api/context/memory/company/expire',
        intent: 'company-memory-expire',
        body: { ticker: 'BHP', entry_id: 1, note: 'expire' },
      },
      {
        name: 'sector add',
        call: postMarketAdd,
        path: '/api/cockpit/memory/market/add',
        backendPath: '/api/context/memory/market/add',
        intent: 'sector-memory-add',
        body: { scope: 'sector', ticker: 'BHP', type: 'sector_trend', statement: 'sector note' },
      },
      {
        name: 'sector expire',
        call: postMarketExpire,
        path: '/api/cockpit/memory/market/expire',
        backendPath: '/api/context/memory/market/expire',
        intent: 'sector-memory-expire',
        body: { scope: 'sector', entry_id: 2, note: 'expire' },
      },
      {
        name: 'macro add',
        call: postMarketAdd,
        path: '/api/cockpit/memory/market/add',
        backendPath: '/api/context/memory/market/add',
        intent: 'macro-memory-add',
        body: { scope: 'macro', macro_topic: 'macro', type: 'macro_theme', statement: 'macro note' },
      },
      {
        name: 'macro expire',
        call: postMarketExpire,
        path: '/api/cockpit/memory/market/expire',
        backendPath: '/api/context/memory/market/expire',
        intent: 'macro-memory-expire',
        body: { scope: 'macro', entry_id: 3, note: 'expire' },
      },
      {
        name: 'thesis proposal create',
        call: postThesisProposal,
        path: '/api/cockpit/memory/thesis/proposals',
        backendPath: '/api/context/thesis/proposals',
        intent: 'thesis-proposal-create',
        body: { ticker: 'BHP', proposal_type: 'create_thesis', statement: 'proposal note' },
      },
      {
        name: 'thesis proposal confirm',
        call: (request) => postThesisConfirm(request, proposalContext()),
        path: '/api/cockpit/memory/thesis/proposals/proposal-1/confirm',
        backendPath: '/api/context/thesis/proposals/proposal-1/confirm',
        intent: 'thesis-proposal-confirm',
        body: { note: 'confirm' },
      },
      {
        name: 'thesis proposal reject',
        call: (request) => postThesisReject(request, proposalContext()),
        path: '/api/cockpit/memory/thesis/proposals/proposal-1/reject',
        backendPath: '/api/context/thesis/proposals/proposal-1/reject',
        intent: 'thesis-proposal-reject',
        body: { note: 'reject' },
      },
      {
        name: 'thesis proposal apply',
        call: (request) => postThesisApply(request, proposalContext()),
        path: '/api/cockpit/memory/thesis/proposals/proposal-1/apply',
        backendPath: '/api/context/thesis/proposals/proposal-1/apply',
        intent: 'thesis-proposal-apply',
        body: { note: 'apply' },
      },
    ]

    for (const item of cases) {
      const response = await item.call(memoryWriteRequest(item.path, item.body, item.intent))
      expect(response.status, item.name).toBe(200)
    }

    expect(fetchMock).toHaveBeenCalledTimes(cases.length)
    cases.forEach((item, index) => {
      const call = fetchMock.mock.calls[index]
      expect(call?.[0], item.name).toBe(`http://backend.internal:8000${item.backendPath}`)
      const init = call?.[1] as RequestInit
      expect(init.method, item.name).toBe('POST')
      expect((init.headers as Headers).get(MEMORY_WRITE_INTENT_HEADER), item.name).toBe(item.intent)
      expect(JSON.parse(String(init.body)), item.name).toMatchObject({
        ...item.body,
        intent: item.intent,
        confirmation: MEMORY_WRITE_CONFIRMATION,
      })
    })
  })
})
