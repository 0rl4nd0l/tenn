import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET as getCockpitHomeRoute } from '@/app/api/cockpit/home/route';
import { buildCockpitHomeBffResponse } from './cockpit-home-api';

describe('Cockpit Home BFF route', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('assembles a partial Home response from safe backend HTTP surfaces', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000';
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'ok',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              ticker: 'BHP',
              quantity: 10,
              current_price: 100,
              price_currency: 'AUD',
              price_as_of: '2026-05-07T01:00:00Z',
              market_value: 1000,
            },
            {
              ticker: 'CBA',
              quantity: 2,
              current_price: null,
              price_currency: null,
              price_as_of: null,
              market_value: null,
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          count: 1,
          items: [
            {
              source_id: 'youtube_transcript:video-a:111',
              source_type: 'youtube_transcript',
              source_name: 'BHP operating update',
              approved_at: '2026-05-06T10:00:00Z',
            },
          ],
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const response = await getCockpitHomeRoute(
      new NextRequest('http://localhost/api/cockpit/home', {
        headers: { 'X-API-Key': 'test-key' },
      }),
    );

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      'http://backend.internal:8000/api/health',
      'http://backend.internal:8000/api/cockpit/holdings',
      'http://backend.internal:8000/api/commentary/recent?limit=5',
    ]);
    for (const call of fetchMock.mock.calls) {
      const init = call[1] as RequestInit;
      expect((init.headers as Headers).get('X-API-Key')).toBe('test-key');
      expect(init.cache).toBe('no-store');
    }

    const payload = await response.json();
    expect(response.status).toBe(200);
    expect(payload.ok).toBe(true);
    expect(payload.source_label_taxonomy_version).toBe('source_label_semantics_v1');
    expect(payload.data_state).toBe('PARTIAL');
    expect(payload.portfolio).toMatchObject({
      data_state: 'PARTIAL',
      total_value: 1000,
      holdings_count: 2,
      priced_holdings_count: 1,
      coverage_percent: 50,
      day_change: null,
      day_change_percent: null,
    });
    expect(payload.market_session).toMatchObject({
      data_state: 'DATA_MISSING',
      session: 'DEGRADED',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
    });
    expect(payload.news[0]).toMatchObject({
      id: 'home-news:youtube_transcript:video-a:111',
      headline: 'BHP operating update',
      source_name: 'youtube_transcript',
      evidence: {
        source_id: 'youtube_transcript:video-a:111',
        source_kind: 'ephemeral',
        source_label: 'context_only',
        evidence_labels: ['context_only'],
        resolvable: true,
        resolver: 'cockpit_chat_attached_sources',
      },
    });
    expect(payload.market_movers[0].state.data_state).toBe('DATA_MISSING');
    expect(payload.attention_queue[0].state.data_state).toBe('DATA_MISSING');
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).toContain(
      'NO_MARKET_SESSION_ENDPOINT',
    );
  });

  it('returns DATA_MISSING without fabricating source-backed evidence when upstreams fail', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('connect ECONNREFUSED'));

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(payload.ok).toBe(true);
    expect(payload.generated_at).toBe('2026-05-07T02:00:00.000Z');
    expect(payload.data_state).toBe('DATA_MISSING');
    expect(payload.degraded).toBe(true);
    expect(payload.portfolio.total_value).toBeNull();
    expect(payload.news).toEqual([]);
    expect(payload.market_movers[0].evidence).toMatchObject({
      source_id: null,
      source_kind: null,
      source_label: 'missing_required_evidence',
      resolvable: false,
      resolver: 'none',
    });
    expect(payload.data_missing.map((signal) => signal.code)).toEqual(
      expect.arrayContaining([
        'HOLDINGS_ENDPOINT_UNAVAILABLE',
        'COMMENTARY_RECENT_UNAVAILABLE',
        'NO_MARKET_SESSION_ENDPOINT',
      ]),
    );
  });

  it('does not aggregate currency-less portfolio totals across mixed currencies', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            { ticker: 'BHP', market_value: 1000, price_currency: 'AUD' },
            { ticker: 'AAPL', market_value: 500, price_currency: 'USD' },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ items: [] }));

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(payload.portfolio.total_value).toBeNull();
    expect(payload.portfolio.data_state).toBe('PARTIAL');
    expect(payload.portfolio.data_missing.map((signal) => signal.code)).toContain(
      'PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS',
    );
  });

  it('marks commentary rows without source ids as DATA_MISSING and unresolvable', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              source_name: 'Untyped commentary',
              source_type: 'market_commentary',
              approved_at: '2026-05-06T10:00:00Z',
            },
          ],
        }),
      );

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(payload.news[0]).toMatchObject({
      state: {
        data_state: 'DATA_MISSING',
      },
      evidence: {
        source_id: null,
        source_kind: null,
        source_label: 'missing_required_evidence',
        resolvable: false,
        resolver: 'none',
      },
    });
    expect(payload.news[0].state.data_missing.map((signal) => signal.code)).toContain(
      'RECENT_COMMENTARY_SOURCE_ID_MISSING',
    );
  });
});

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
    },
  });
}
