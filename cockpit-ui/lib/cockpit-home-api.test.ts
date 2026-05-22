import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { createElement } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { GET as getCockpitHomeRoute } from '@/app/api/cockpit/home/route';
import { CockpitHomePage } from '@/components/cockpit/home/home-page';
import {
  HOME_PORTFOLIO_UPSTREAM_TIMEOUT_MS,
  buildCockpitHomeBffResponse,
} from './cockpit-home-api';
import type {
  CockpitHomeBffResponse,
  CockpitHomeDataMissingSignal,
} from '@/types/cockpit-home';

describe('Cockpit Home BFF route', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL;
    vi.useRealTimers();
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
      )
      .mockResolvedValueOnce(
        jsonResponse({
          ok: true,
          data_state: 'PARTIAL',
          degraded: false,
          data_missing: [
            signal(
              'market_movers',
              'MARKET_MOVER_PRICE_FIELDS_MISSING',
              'Market update follow-up did not include deterministic price, change, and change-percent fields.',
              'operational_trace',
            ),
          ],
          as_of: '2026-05-07T01:15:00Z',
          items: [
            {
              id: 'home-market-movers:market_update_followup:fu-1',
              title: 'BHP: review',
              ticker: 'BHP',
              reason: 'notable price move',
              observed_at: '2026-05-07T01:15:00Z',
              price: null,
              change: null,
              change_percent: null,
              data_state: 'PARTIAL',
              degraded: false,
              data_missing: [
                signal(
                  'market_movers',
                  'MARKET_MOVER_PRICE_FIELDS_MISSING',
                  'Market update follow-up did not include deterministic price, change, and change-percent fields.',
                  'operational_trace',
                ),
              ],
              as_of: '2026-05-07T01:15:00Z',
              source_label: 'operational_trace',
              evidence_id: 'market_update_followup:fu-1',
            },
          ],
        }),
      )
      .mockResolvedValueOnce(jsonResponse(narrativeMissingResponse()));
    vi.stubGlobal('fetch', fetchMock);

    const response = await getCockpitHomeRoute(
      new NextRequest('http://localhost/api/cockpit/home', {
        headers: { 'X-API-Key': 'test-key' },
      }),
    );

	    expect(fetchMock).toHaveBeenCalledTimes(7);
	    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
	      'http://backend.internal:8000/api/health',
	      'http://backend.internal:8000/api/cockpit/home/market-session',
	      'http://backend.internal:8000/api/cockpit/home/portfolio',
	      'http://backend.internal:8000/api/commentary/recent?limit=5',
	      'http://backend.internal:8000/api/cockpit/home/attention-queue',
	      'http://backend.internal:8000/api/cockpit/home/market-movers',
	      'http://backend.internal:8000/api/cockpit/home/narrative',
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
    expect(payload.market_movers[0]).toMatchObject({
      id: 'home-market-movers:market_update_followup:fu-1',
      title: 'BHP: review',
      ticker: 'BHP',
      state: {
        data_state: 'PARTIAL',
      },
      evidence: {
        source_id: null,
        source_label: 'operational_trace',
        evidence_labels: ['operational_trace'],
        resolvable: false,
        resolver: 'none',
      },
      price: null,
      change: null,
      change_percent: null,
      reason: 'notable price move',
    });
    expect(payload.market_movers[0].state.data_missing.map((signal: { code: string }) => signal.code)).toContain(
      'MARKET_MOVER_PRICE_FIELDS_MISSING',
    );
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
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).toContain(
      'MARKET_MOVER_PRICE_FIELDS_MISSING',
    );
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).not.toContain(
      'NO_MARKET_SESSION_ENDPOINT',
    );
    expect(payload.data_missing.map((signal: { code: string }) => signal.code)).not.toContain(
      'NO_ATTENTION_QUEUE_ENDPOINT',
    );
  });

  it('does not block /api/cockpit/home on a slow portfolio upstream', async () => {
    vi.useFakeTimers();
    process.env.NEXT_PUBLIC_API_URL = 'http://backend.internal:8000';
    const slowPortfolioDelayMs = HOME_PORTFOLIO_UPSTREAM_TIMEOUT_MS + 9_000;
    const upstreamTimings: TimedHomeUpstreamCall[] = [];
    const fetchMock = timedHomeFetcher(
      [
        timedUpstream('/api/health', 1, { status: 'ok' }),
        timedUpstream('/api/cockpit/home/market-session', 2, marketSessionResponse()),
        timedUpstream('/api/cockpit/home/portfolio', slowPortfolioDelayMs, portfolioResponse()),
        timedUpstream('/api/commentary/recent?limit=5', 3, { items: [] }),
        timedUpstream('/api/cockpit/home/attention-queue', 2, {
          ok: true,
          data_state: 'READY',
          degraded: false,
          data_missing: [],
          as_of: '2026-05-07T02:00:00Z',
          items: [],
        }),
        timedUpstream('/api/cockpit/home/market-movers', 2, marketMoversEmptyResponse()),
        timedUpstream('/api/cockpit/home/narrative', 2, narrativeMissingResponse()),
      ],
      upstreamTimings,
    );
    vi.stubGlobal('fetch', fetchMock);

    const responsePromise = getCockpitHomeRoute(new NextRequest('http://localhost/api/cockpit/home'));

    await vi.advanceTimersByTimeAsync(HOME_PORTFOLIO_UPSTREAM_TIMEOUT_MS);
    const response = await responsePromise;
    const payload = (await response.json()) as CockpitHomeBffResponse;

    expect(response.status).toBe(200);
    expectHomeBffBodyShape(payload);
    expect(fetchMock).toHaveBeenCalledTimes(7);
    expect(upstreamTimings.map((timing) => timing.path)).not.toContain('/api/cockpit/home/portfolio');
    expect(payload.data_state).toBe('PARTIAL');
    expect(payload.portfolio).toMatchObject({
      data_state: 'DATA_MISSING',
      degraded: true,
      source_label: 'local_personal_data',
      total_value: null,
      currency: null,
      day_change: null,
      day_change_percent: null,
      coverage_percent: null,
      holdings_count: 0,
      priced_holdings_count: 0,
      day_change_priced_holdings_count: 0,
    });
    expect(payload.portfolio.data_missing).toEqual([
      expect.objectContaining({
        section: 'portfolio',
        code: 'PORTFOLIO_ENDPOINT_UNAVAILABLE',
        message: expect.stringContaining(`timed out after ${HOME_PORTFOLIO_UPSTREAM_TIMEOUT_MS}ms`),
        source_label: 'missing_required_evidence',
      }),
    ]);
    expect(payload.data_missing.map((signal) => signal.code)).toContain('PORTFOLIO_ENDPOINT_UNAVAILABLE');
    expect(payload.data_health.find((item) => item.section === 'portfolio')).toMatchObject({
      data_state: 'DATA_MISSING',
      degraded: true,
      value: 'DATA_MISSING',
    });
  });

  it('returns DATA_MISSING without fabricating source-backed evidence when upstreams fail', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('connect ECONNREFUSED'));

    const payload = await buildCockpitHomeBffResponse({
      now: new Date('2026-05-07T02:00:00Z'),
      backendUrl: 'http://backend.internal:8000',
      fetcher,
    });

    expect(fetcher).toHaveBeenCalledTimes(7);
    expect(payload.ok).toBe(true);
    expect(payload.generated_at).toBe('2026-05-07T02:00:00.000Z');
    expect(payload.data_state).toBe('DATA_MISSING');
    expect(payload.degraded).toBe(true);
    expect(payload.portfolio.total_value).toBeNull();
    expect(payload.news).toEqual([]);
    expect(payload.market_movers).toEqual([]);
    expect(payload.data_missing.map((signal) => signal.code)).toEqual(
      expect.arrayContaining([
        'PORTFOLIO_ENDPOINT_UNAVAILABLE',
        'COMMENTARY_RECENT_UNAVAILABLE',
        'MARKET_SESSION_ENDPOINT_UNAVAILABLE',
        'NO_ATTENTION_QUEUE_ENDPOINT',
        'MARKET_MOVERS_ENDPOINT_UNAVAILABLE',
        'HOME_NARRATIVE_ENDPOINT_UNAVAILABLE',
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
      .mockResolvedValueOnce(attentionQueueResponse([]))
      .mockResolvedValueOnce(jsonResponse(marketMoversEmptyResponse()))
      .mockResolvedValueOnce(jsonResponse(narrativeMissingResponse()));

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
      .mockResolvedValueOnce(attentionQueueResponse([]))
      .mockResolvedValueOnce(jsonResponse(marketMoversEmptyResponse()))
      .mockResolvedValueOnce(jsonResponse(narrativeMissingResponse()));

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
      .mockResolvedValueOnce(attentionQueueResponse([]))
      .mockResolvedValueOnce(jsonResponse(marketMoversEmptyResponse()))
      .mockResolvedValueOnce(jsonResponse(narrativeMissingResponse()));

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
    vi.useRealTimers();
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
    expect(screen.getAllByText('PORTFOLIO_DAY_CHANGE_PARTIAL').length).toBeGreaterThan(0);
    expect(screen.getByText('CONTEXT ONLY')).toBeInTheDocument();
    expect(screen.getByLabelText('Open portfolio holdings')).toHaveAttribute('href', '/holdings');
    expect(screen.getByLabelText('Open news workspace')).toHaveAttribute('href', '/news');
    expect(screen.getByText('Home context')).toBeInTheDocument();
    expect(screen.getByText('Home has partial context available. Full Chat opens a draft for the visible, source-labeled Home state.')).toBeInTheDocument();
    expect(screen.getByLabelText('Open full chat with Home context')).toHaveAttribute(
      'href',
      "/full-chat?prompt=Summarize+today%27s+available+Home+context.",
    );
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();
  });

  it('renders Useful Now from existing Home signals without upgrading missing state', async () => {
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
          target_route: '/news',
        },
      ],
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)));

    render(createElement(CockpitHomePage));

    const panel = await screen.findByTestId('home-useful-now-panel');
    expect(within(panel).getByText('Useful Now')).toBeInTheDocument();
    expect(within(panel).getByText('Review BHP: review')).toBeInTheDocument();
    expect(within(panel).getByRole('link', { name: 'Open useful now action: Review BHP: review' })).toHaveAttribute(
      'href',
      '/news',
    );
    expect(within(panel).getByRole('button', { name: 'Inspect useful now source: BHP operating update' })).toBeInTheDocument();
    expect(within(panel).getByText('Portfolio gap')).toBeInTheDocument();
    expect(within(panel).getByText('PORTFOLIO_DAY_CHANGE_PARTIAL')).toBeInTheDocument();
    expect(within(panel).queryByText('CLAIM VERIFIED')).not.toBeInTheDocument();
  });

  it('loads source detail for resolvable Home commentary sources', async () => {
    const payload = homeBffPayload();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(payload))
      .mockResolvedValueOnce(
        jsonResponse({
          ok: true,
          source_id: 'youtube_transcript:source-a',
          source_status: 'staged',
          source_name: 'BHP operating update',
          published_at: '2026-05-07T02:00:00Z',
          chunk_count: 3,
          memo_status: 'ready',
          takeaway_source: 'chunks',
          takeaways: [{ text: 'BHP management highlighted iron ore cost discipline.' }],
          model: 'deterministic:commentary-staged-chunks',
          prompt_version: 'takeaways-v1-deterministic',
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();

    render(createElement(CockpitHomePage));

    await user.click(await screen.findByText('BHP operating update'));

    expect(await screen.findByText('BHP management highlighted iron ore cost discipline.')).toBeInTheDocument();
    expect(screen.getByText('Source Status')).toBeInTheDocument();
    expect(screen.getByText('staged')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/cockpit/commentary/takeaways',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ source_id: 'youtube_transcript:source-a', limit: 3 }),
        cache: 'no-store',
      }),
    );
  });

  it('renders backend attention queue items without mock substitution', async () => {
    const base = homeBffPayload();
    const moverPriceMissing = signal(
      'market_movers',
      'MARKET_MOVER_PRICE_FIELDS_MISSING',
      'Market update follow-up did not include deterministic price, change, and change-percent fields.',
      'operational_trace',
    );
    const payload = homeBffPayload({
      data_missing: [
        ...base.data_missing.filter((signal) => signal.section !== 'attention_queue' && signal.section !== 'market_movers'),
        moverPriceMissing,
      ],
      market_movers: [
        {
          id: 'home-market-movers:market_update_followup:fu-1',
          section: 'market_movers',
          title: 'BHP: review',
          ticker: 'BHP',
          observed_at: '2026-05-07T01:15:00Z',
          state: {
            data_state: 'PARTIAL',
            degraded: false,
            data_missing: [moverPriceMissing],
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
          price: null,
          change: null,
          change_percent: null,
          reason: 'notable price move',
        },
      ],
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
          target_route: '/news',
        },
      ],
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)));

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Market Update Signals')).toBeInTheDocument();
    expect(screen.getAllByText('BHP: review').length).toBeGreaterThan(0);
    expect(screen.getByText('MARKET_MOVER_PRICE_FIELDS_MISSING')).toBeInTheDocument();
    expect(screen.getAllByText('notable price move').length).toBeGreaterThan(0);
    expect(screen.getAllByText('queued').length).toBeGreaterThan(0);
    expect(screen.getAllByText('market_update_followup').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Open attention item: BHP: review')).toHaveAttribute('href', '/news');
    expect(screen.queryByText('NO_ATTENTION_QUEUE_ENDPOINT')).not.toBeInTheDocument();
    expect(screen.queryByText(/WiseTech Global/i)).not.toBeInTheDocument();
  });

  it('renders live backend narrative summary and tomorrow prep', async () => {
    const payload = homeBffPayload({
      narrative: {
        data_state: 'READY',
        degraded: false,
        data_missing: [],
        as_of: '2026-05-07T02:00:00Z',
        session_summary: 'Backend session summary says defensives led while miners lagged.',
        theme_candidates: [
          {
            label: 'Defensive rotation',
            sentiment: 'positive',
            evidenceCount: 2,
            description: 'Healthcare and staples commentary carried the strongest source-backed signal.',
          },
        ],
        tomorrow_prep: ['Check BHP opening liquidity.', 'Review portfolio exposure before ASX open.'],
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(payload)));

    render(createElement(CockpitHomePage));

    expect(await screen.findByText('Session Summary')).toBeInTheDocument();
    expect(screen.getByText('Backend session summary says defensives led while miners lagged.')).toBeInTheDocument();
    expect(screen.getByText('Tomorrow Prep')).toBeInTheDocument();
    expect(screen.getByText('Check BHP opening liquidity.')).toBeInTheDocument();
    expect(screen.getByText('Review portfolio exposure before ASX open.')).toBeInTheDocument();
    expect(screen.getByText('Defensive rotation')).toBeInTheDocument();
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
    expect(screen.getAllByText('HOME_RUNTIME_DEGRADED').length).toBeGreaterThan(0);
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

interface TimedHomeUpstream {
  path: string;
  delayMs: number;
  payload: unknown;
}

interface TimedHomeUpstreamCall {
  path: string;
  section: string;
  durationMs: number;
}

function timedUpstream(path: string, delayMs: number, payload: unknown): TimedHomeUpstream {
  return {
    path,
    delayMs,
    payload,
  };
}

function timedHomeFetcher(upstreams: TimedHomeUpstream[], calls: TimedHomeUpstreamCall[]) {
  const upstreamByPath = new Map(upstreams.map((upstream) => [upstream.path, upstream]));
  return vi.fn((input: string) => {
    const url = new URL(input);
    const path = `${url.pathname}${url.search}`;
    const upstream = upstreamByPath.get(path);
    if (!upstream) {
      return Promise.reject(new Error(`Unexpected Home upstream: ${path}`));
    }
    return new Promise<Response>((resolve) => {
      setTimeout(() => {
        calls.push({
          path,
          section: homeSectionForPath(path),
          durationMs: upstream.delayMs,
        });
        resolve(jsonResponse(upstream.payload));
      }, upstream.delayMs);
    });
  });
}

function homeSectionForPath(path: string): string {
  if (path === '/api/health') return 'data_health';
  if (path === '/api/cockpit/home/market-session') return 'market_session';
  if (path === '/api/cockpit/home/portfolio') return 'portfolio';
  if (path === '/api/commentary/recent?limit=5') return 'news';
  if (path === '/api/cockpit/home/attention-queue') return 'attention_queue';
  if (path === '/api/cockpit/home/market-movers') return 'market_movers';
  if (path === '/api/cockpit/home/narrative') return 'session_summary';
  return 'unknown';
}

function expectHomeBffBodyShape(payload: CockpitHomeBffResponse): void {
  expect(payload).toMatchObject({
    ok: true,
    source_label_taxonomy_version: 'source_label_semantics_v1',
  });
  expect(typeof payload.generated_at).toBe('string');
  expect(['READY', 'PARTIAL', 'DEGRADED', 'DATA_MISSING']).toContain(payload.data_state);
  expect(Array.isArray(payload.data_missing)).toBe(true);
  expect(payload.market_session.exchange).toBe('ASX');
  expect(payload.market_session.timezone).toBe('Australia/Melbourne');
  expect(payload.portfolio.source_label).toBe('local_personal_data');
  expect(Array.isArray(payload.market_movers)).toBe(true);
  expect(Array.isArray(payload.news)).toBe(true);
  expect(Array.isArray(payload.attention_queue)).toBe(true);
  expect(Array.isArray(payload.data_health)).toBe(true);
  expect(payload.narrative).toMatchObject({
    session_summary: null,
    theme_candidates: [],
    tomorrow_prep: [],
  });
  expect(payload.data_health.map((item) => item.section)).toEqual([
    'data_health',
    'market_session',
    'portfolio',
    'news',
    'attention_queue',
    'market_movers',
    'session_summary',
  ]);
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

function marketMoversEmptyResponse() {
  return {
    ok: true,
    data_state: 'DATA_MISSING',
    degraded: true,
    data_missing: [
      signal(
        'market_movers',
        'NO_MARKET_UPDATE_SIGNALS',
        'No queued market-update follow-up signals are available for Cockpit Home.',
        'no_hit',
      ),
    ],
    as_of: '2026-05-07T02:00:00Z',
    items: [],
  };
}

function narrativeMissingResponse() {
  return {
    ok: true,
    data_state: 'DATA_MISSING',
    degraded: true,
    data_missing: [
      signal(
        'session_summary',
        'NO_SESSION_SUMMARY_ENDPOINT',
        'No backend session-summary producer is available for Cockpit Home v1.',
      ),
      signal(
        'theme_candidates',
        'NO_THEME_CANDIDATES_ENDPOINT',
        'No backend theme-candidates producer is available for Cockpit Home v1.',
      ),
      signal(
        'tomorrow_prep',
        'NO_TOMORROW_PREP_ENDPOINT',
        'No backend tomorrow-prep producer is available for Cockpit Home v1.',
      ),
    ],
    as_of: '2026-05-07T02:00:00Z',
    session_summary: null,
    theme_candidates: [],
    tomorrow_prep: [],
  };
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
