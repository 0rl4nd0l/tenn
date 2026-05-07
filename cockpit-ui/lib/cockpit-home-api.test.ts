import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { createElement } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { GET as getCockpitHomeRoute } from '@/app/api/cockpit/home/route';
import { CockpitHomePage } from '@/components/cockpit/home/home-page';
import { buildCockpitHomeBffResponse } from './cockpit-home-api';
import type {
  CockpitHomeBffResponse,
  CockpitHomeDataMissingSignal,
} from '@/types/cockpit-home';

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

describe('CockpitHomePage live BFF wiring', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders an explicit loading state while GET /api/cockpit/home is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)));

    render(createElement(CockpitHomePage));

    expect(screen.getByTestId('home-loading-state')).toHaveTextContent('Loading Cockpit Home');
    expect(screen.getByText('GET /api/cockpit/home')).toBeInTheDocument();
  });

  it('loads partial BFF state without hiding missing portfolio fields behind mock data', async () => {
    const payload = homeBffPayload();
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload));
    vi.stubGlobal('fetch', fetchMock);

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Home state: PARTIAL')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/home',
      expect.objectContaining({ cache: 'no-store' }),
    );
    expect(screen.getByText('A$1,000.00')).toBeInTheDocument();
    expect(screen.getByText('Local personal holdings data only. This panel is not canonical financial truth.')).toBeInTheDocument();
    expect(screen.getAllByText('DATA_MISSING').length).toBeGreaterThan(0);
    expect(screen.getByText('PORTFOLIO_DAY_CHANGE_UNAVAILABLE')).toBeInTheDocument();
    expect(screen.getByText('CONTEXT ONLY')).toBeInTheDocument();
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();
  });

  it('renders backend DATA_MISSING state visibly instead of substituting mock news', async () => {
    const payload = homeBffPayload({
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [signal('news', 'NO_RECENT_COMMENTARY', 'Recent commentary endpoint returned no approved commentary sources.')],
      news: [],
    });
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload));
    vi.stubGlobal('fetch', fetchMock);

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Home state: DATA_MISSING')).toBeInTheDocument();
    expect(screen.getAllByText('NO_RECENT_COMMENTARY').length).toBeGreaterThan(0);
    expect(screen.getByText('The backend did not provide resolvable Home news items.')).toBeInTheDocument();
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();
  });

  it('renders degraded BFF state without upgrading runtime evidence trust', async () => {
    const degradedSignal = signal('data_health', 'HOME_RUNTIME_DEGRADED', 'Home runtime is degraded.', 'degraded_runtime');
    const payload = homeBffPayload({
      data_state: 'DEGRADED',
      degraded: true,
      data_missing: [degradedSignal],
      market_session: {
        ...homeBffPayload().market_session,
        data_state: 'DEGRADED',
        degraded: true,
        data_missing: [degradedSignal],
        session: 'DEGRADED',
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)));

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Home state: DEGRADED')).toBeInTheDocument();
    expect(screen.getByText('DEGRADED STATE')).toBeInTheDocument();
    expect(screen.getByText('HOME_RUNTIME_DEGRADED')).toBeInTheDocument();
  });

  it('does not silently source-back mock fallback fixtures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    const user = userEvent.setup();

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Cockpit Home BFF unavailable')).toBeInTheDocument();
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'DEMO OPEN' }));

    expect(await screen.findByText('DEMO FIXTURE')).toBeInTheDocument();
    expect(screen.getByText('DEMO_FIXTURE_NOT_SOURCE_BACKED')).toBeInTheDocument();
    expect(screen.getByText(/DEMO FIXTURE: ASX Announcement/i)).toBeInTheDocument();
    expect(screen.getAllByText('UNKNOWN UNCLASSIFIED').length).toBeGreaterThan(0);
    expect(screen.queryByText('CLAIM VERIFIED')).not.toBeInTheDocument();
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

function homeBffPayload(overrides: Partial<CockpitHomeBffResponse> = {}): CockpitHomeBffResponse {
  const now = '2026-05-07T02:00:00.000Z';
  const marketMissing = signal(
    'market_session',
    'NO_MARKET_SESSION_ENDPOINT',
    'No backend market-session endpoint is available for Cockpit Home v1.',
  );
  const portfolioPartial = signal(
    'portfolio',
    'PORTFOLIO_DAY_CHANGE_UNAVAILABLE',
    'Backend holdings endpoint does not provide deterministic portfolio day-change fields.',
  );
  const moversMissing = signal(
    'market_movers',
    'NO_MARKET_MOVERS_ENDPOINT',
    'No backend market-movers endpoint is available for Cockpit Home v1.',
  );
  const attentionMissing = signal(
    'attention_queue',
    'NO_ATTENTION_QUEUE_ENDPOINT',
    'No backend attention-queue endpoint is available for Cockpit Home v1.',
  );
  const narrativeMissing = signal(
    'session_summary',
    'NO_SESSION_SUMMARY_ENDPOINT',
    'No backend session-summary endpoint is available for Cockpit Home v1.',
  );

  return {
    ok: true,
    generated_at: now,
    source_label_taxonomy_version: 'source_label_semantics_v1',
    data_state: 'PARTIAL',
    degraded: false,
    data_missing: [marketMissing, portfolioPartial, moversMissing, attentionMissing, narrativeMissing],
    as_of: now,
    market_session: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [marketMissing],
      as_of: null,
      session: 'DEGRADED',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      session_date: '2026-05-07',
      next_event_label: null,
      next_event_at: null,
    },
    portfolio: {
      data_state: 'PARTIAL',
      degraded: false,
      data_missing: [portfolioPartial],
      as_of: now,
      total_value: 1000,
      day_change: null,
      day_change_percent: null,
      coverage_percent: 50,
      holdings_count: 2,
      priced_holdings_count: 1,
    },
    market_movers: [
      {
        id: 'home-market-movers:data-missing',
        section: 'market_movers',
        title: 'Market movers unavailable',
        ticker: '',
        observed_at: now,
        state: {
          data_state: 'DATA_MISSING',
          degraded: true,
          data_missing: [moversMissing],
          as_of: now,
        },
        evidence: missingEvidence(),
        price: null,
        change: null,
        change_percent: null,
        reason: null,
      },
    ],
    news: [
      {
        id: 'home-news:source-a',
        section: 'news',
        title: 'BHP operating update',
        ticker: 'BHP',
        observed_at: now,
        state: {
          data_state: 'READY',
          degraded: false,
          data_missing: [],
          as_of: now,
        },
        evidence: {
          source_id: 'youtube_transcript:source-a',
          source_kind: 'ephemeral',
          source_label: 'context_only',
          evidence_labels: ['context_only'],
          resolvable: true,
          resolver: 'cockpit_chat_attached_sources',
          evidence_id: 'youtube_transcript:source-a',
          document_id: null,
          chunk_id: null,
          url: null,
          title: 'BHP operating update',
          published_at: now,
        },
        headline: 'BHP operating update',
        source_name: 'youtube_transcript',
        relevance: 'medium',
      },
    ],
    attention_queue: [
      {
        id: 'home-attention-queue:data-missing',
        section: 'attention_queue',
        title: 'Attention queue unavailable',
        observed_at: now,
        state: {
          data_state: 'DATA_MISSING',
          degraded: true,
          data_missing: [attentionMissing],
          as_of: now,
        },
        evidence: missingEvidence(),
        priority: 'low',
        description: 'No backend attention-queue data is available for Cockpit Home v1.',
      },
    ],
    data_health: [
      {
        data_state: 'READY',
        degraded: false,
        data_missing: [],
        as_of: now,
        section: 'data_health',
        label: 'Backend liveness',
        value: 'HTTP 200',
      },
      {
        data_state: 'PARTIAL',
        degraded: false,
        data_missing: [portfolioPartial],
        as_of: now,
        section: 'portfolio',
        label: 'Holdings',
        value: '1/2 priced',
      },
      {
        data_state: 'DATA_MISSING',
        degraded: true,
        data_missing: [moversMissing],
        as_of: now,
        section: 'market_movers',
        label: 'Market movers',
        value: 'DATA_MISSING',
      },
    ],
    narrative: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [narrativeMissing],
      as_of: now,
      session_summary: null,
      theme_candidates: [],
      tomorrow_prep: [],
    },
    ...overrides,
  };
}

function signal(
  section: CockpitHomeDataMissingSignal['section'],
  code: string,
  message: string,
  sourceLabel: NonNullable<CockpitHomeDataMissingSignal['source_label']> = 'missing_required_evidence',
): CockpitHomeDataMissingSignal {
  return {
    section,
    code,
    message,
    source_id: null,
    evidence_id: null,
    source_label: sourceLabel,
  };
}

function missingEvidence() {
  return {
    source_id: null,
    source_kind: null,
    source_label: 'missing_required_evidence' as const,
    evidence_labels: ['missing_required_evidence' as const],
    resolvable: false,
    resolver: 'none' as const,
    evidence_id: null,
    document_id: null,
    chunk_id: null,
    url: null,
    title: null,
    published_at: null,
  };
}
