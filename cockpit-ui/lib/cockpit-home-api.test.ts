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
      .mockResolvedValueOnce(jsonResponse(marketSessionResponse()))
      .mockResolvedValueOnce(
        jsonResponse(
          portfolioResponse({
            data_state: 'PARTIAL',
            data_missing: [
              signal(
                'portfolio',
                'PORTFOLIO_PRICING_PARTIAL',
                'Only 1/2 local holdings have deterministic current price and quantity fields.',
                'local_personal_data',
              ),
              signal(
                'portfolio',
                'PORTFOLIO_DAY_CHANGE_PARTIAL',
                'Only 1/2 local holdings include deterministic previous-close inputs for portfolio day-change.',
                'local_personal_data',
              ),
            ],
            as_of: '2026-05-07T01:00:00Z',
            total_value: 1000,
            currency: 'AUD',
            day_change: 20,
            day_change_percent: 2.04,
            coverage_percent: 50,
            holdings_count: 2,
            priced_holdings_count: 1,
            day_change_priced_holdings_count: 1,
          }),
        ),
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
      )
      .mockResolvedValueOnce(
        jsonResponse({
          ok: true,
          data_state: 'READY',
          degraded: false,
          data_missing: [],
          as_of: '2026-05-07T01:15:00Z',
          items: [
            {
              id: 'market_update_followup:fu-1',
              title: 'BHP: review',
              reason: 'notable price move',
              status: 'queued',
              priority: 'high',
              source_type: 'market_update_followup',
              created_at: '2026-05-07T01:15:00Z',
              updated_at: '2026-05-07T01:15:00Z',
              source_id: null,
              target_route: null,
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

	    expect(fetchMock).toHaveBeenCalledTimes(5);
	    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
	      'http://backend.internal:8000/api/health',
	      'http://backend.internal:8000/api/cockpit/home/market-session',
	      'http://backend.internal:8000/api/cockpit/home/portfolio',
	      'http://backend.internal:8000/api/commentary/recent?limit=5',
	      'http://backend.internal:8000/api/cockpit/home/attention-queue',
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
      currency: 'AUD',
      holdings_count: 2,
      priced_holdings_count: 1,
      day_change_priced_holdings_count: 1,
      coverage_percent: 50,
      day_change: 20,
      day_change_percent: 2.04,
      source_label: 'local_personal_data',
    });
    expect(payload.market_session).toMatchObject({
      data_state: 'READY',
      session: 'OPEN',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      next_event_label: 'ASX close',
      next_event_at: '2026-05-07T06:00:00+00:00',
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
    expect(payload.attention_queue_state.data_state).toBe('READY');
    expect(payload.attention_queue[0]).toMatchObject({
      id: 'market_update_followup:fu-1',
      title: 'BHP: review',
      priority: 'high',
      status: 'queued',
      source_type: 'market_update_followup',
      evidence: {
        source_id: null,
        source_label: 'operational_trace',
        evidence_labels: ['operational_trace'],
        resolvable: false,
        resolver: 'none',
      },
    });
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).toContain(
      'PORTFOLIO_DAY_CHANGE_PARTIAL',
    );
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).not.toContain(
      'NO_MARKET_SESSION_ENDPOINT',
    );
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).not.toContain(
      'NO_ATTENTION_QUEUE_ENDPOINT',
    );
  });

  it('returns DATA_MISSING without fabricating source-backed evidence when upstreams fail', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('connect ECONNREFUSED'));

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(fetcher).toHaveBeenCalledTimes(5);
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
        'PORTFOLIO_ENDPOINT_UNAVAILABLE',
        'COMMENTARY_RECENT_UNAVAILABLE',
        'MARKET_SESSION_ENDPOINT_UNAVAILABLE',
        'NO_ATTENTION_QUEUE_ENDPOINT',
      ]),
    );
  });

  it('does not aggregate currency-less portfolio totals across mixed currencies', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
      .mockResolvedValueOnce(jsonResponse(marketSessionResponse()))
      .mockResolvedValueOnce(
        jsonResponse(
          portfolioResponse({
            data_state: 'PARTIAL',
            data_missing: [
              signal(
                'portfolio',
                'PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS',
                'Priced local holdings use multiple currencies, so Cockpit Home did not aggregate a mixed-currency total value.',
                'local_personal_data',
              ),
            ],
            total_value: null,
            currency: null,
            day_change: null,
            day_change_percent: null,
            holdings_count: 2,
            priced_holdings_count: 2,
            day_change_priced_holdings_count: 2,
          }),
        ),
      )
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(attentionQueueResponse([]));

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

  it('keeps empty local holdings as a valid ready portfolio state', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
      .mockResolvedValueOnce(jsonResponse(marketSessionResponse()))
      .mockResolvedValueOnce(jsonResponse(portfolioResponse()))
      .mockResolvedValueOnce(jsonResponse({ items: [] }))
      .mockResolvedValueOnce(attentionQueueResponse([]));

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(payload.portfolio).toMatchObject({
      data_state: 'READY',
      source_label: 'local_personal_data',
      total_value: 0,
      currency: null,
      day_change: 0,
      day_change_percent: 0,
      coverage_percent: 100,
      holdings_count: 0,
      priced_holdings_count: 0,
      day_change_priced_holdings_count: 0,
    });
    expect(payload.portfolio.data_missing).toEqual([]);
  });

  it('marks commentary rows without source ids as DATA_MISSING and unresolvable', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
      .mockResolvedValueOnce(jsonResponse(marketSessionResponse()))
      .mockResolvedValueOnce(jsonResponse(portfolioResponse()))
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
      )
      .mockResolvedValueOnce(attentionQueueResponse([]));

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
    expect(screen.getByText('PORTFOLIO_DAY_CHANGE_PARTIAL')).toBeInTheDocument();
    expect(screen.getByText('CONTEXT ONLY')).toBeInTheDocument();
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();
  });

  it('renders backend attention queue items without mock substitution', async () => {
    const base = homeBffPayload();
    const payload = homeBffPayload({
      data_missing: base.data_missing.filter((signal) => signal.section !== 'attention_queue'),
      attention_queue_state: {
        data_state: 'READY',
        degraded: false,
        data_missing: [],
        as_of: '2026-05-07T01:15:00Z',
      },
      attention_queue: [
        {
          id: 'market_update_followup:fu-1',
          section: 'attention_queue',
          title: 'BHP: review',
          ticker: null,
          observed_at: '2026-05-07T01:15:00Z',
          state: {
            data_state: 'READY',
            degraded: false,
            data_missing: [],
            as_of: '2026-05-07T01:15:00Z',
          },
          evidence: {
            source_id: null,
            source_kind: null,
            source_label: 'operational_trace',
            evidence_labels: ['operational_trace'],
            resolvable: false,
            resolver: 'none',
            evidence_id: 'market_update_followup:fu-1',
            document_id: null,
            chunk_id: null,
            url: null,
            title: 'BHP: review',
            published_at: '2026-05-07T01:15:00Z',
          },
          priority: 'high',
          description: 'notable price move',
          reason: 'notable price move',
          status: 'queued',
          source_type: 'market_update_followup',
          created_at: '2026-05-07T01:15:00Z',
          updated_at: '2026-05-07T01:15:00Z',
          source_id: null,
          target_route: null,
        },
      ],
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)));

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('BHP: review')).toBeInTheDocument();
    expect(screen.getByText('notable price move')).toBeInTheDocument();
    expect(screen.getByText('queued')).toBeInTheDocument();
    expect(screen.getByText('market_update_followup')).toBeInTheDocument();
    expect(screen.queryByText('NO_ATTENTION_QUEUE_ENDPOINT')).not.toBeInTheDocument();
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

function marketSessionResponse() {
  return {
    ok: true,
    exchange: 'ASX',
    timezone: 'Australia/Melbourne',
    session: 'OPEN',
    session_date: '2026-05-07',
    next_event_label: 'ASX close',
    next_event_at: '2026-05-07T06:00:00+00:00',
    as_of: '2026-05-07T02:00:00+00:00',
  };
}

function portfolioResponse(overrides: Record<string, unknown> = {}) {
  return {
    ok: true,
    data_state: 'READY',
    degraded: false,
    data_missing: [],
    as_of: '2026-05-07T01:00:00Z',
    source_label: 'local_personal_data',
    total_value: 0,
    currency: null,
    day_change: 0,
    day_change_percent: 0,
    coverage_percent: 100,
    holdings_count: 0,
    priced_holdings_count: 0,
    day_change_priced_holdings_count: 0,
    ...overrides,
  };
}

function attentionQueueResponse(items: unknown[]) {
  return jsonResponse({
    ok: true,
    data_state: 'READY',
    degraded: false,
    data_missing: [],
    as_of: '2026-05-07T02:00:00Z',
    items,
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
    'PORTFOLIO_DAY_CHANGE_PARTIAL',
    'Only 1/2 local holdings include deterministic previous-close inputs for portfolio day-change.',
    'local_personal_data',
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
      source_label: 'local_personal_data',
      total_value: 1000,
      currency: 'AUD',
      day_change: null,
      day_change_percent: null,
      coverage_percent: 50,
      holdings_count: 2,
      priced_holdings_count: 1,
      day_change_priced_holdings_count: 1,
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
    attention_queue_state: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [attentionMissing],
      as_of: now,
    },
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
        reason: 'No backend attention-queue data is available for Cockpit Home v1.',
        status: 'unavailable',
        source_type: 'missing',
        created_at: now,
        updated_at: now,
        source_id: null,
        target_route: null,
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
