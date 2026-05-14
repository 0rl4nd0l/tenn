import { describe, expect, it } from 'vitest';

import type {
  CockpitHomeBffResponse,
  CockpitHomeDataMissingSignal,
  CockpitHomeDeterministicState,
  CockpitHomeSourceBearingItem,
} from '@/types/cockpit-home';

const RUN_LIVE_SHAPE = process.env.COCKPIT_HOME_LIVE_SHAPE === '1';
const HOME_URL = process.env.COCKPIT_HOME_LIVE_URL ?? 'http://127.0.0.1:8081/api/cockpit/home';
const REQUEST_TIMEOUT_MS = Number(process.env.COCKPIT_HOME_LIVE_TIMEOUT_MS ?? '30000');
const RECOMMENDED_LATENCY_MS = Number(process.env.COCKPIT_HOME_RECOMMENDED_LATENCY_MS ?? '1000');

const describeLive = RUN_LIVE_SHAPE ? describe : describe.skip;

describeLive('Cockpit Home live body-shape guard', () => {
  it('keeps /api/cockpit/home reachable, fast, and honest about partial data', async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const startedAt = performance.now();

    const response = await fetch(HOME_URL, {
      cache: 'no-store',
      signal: controller.signal,
    });
    const elapsedMs = performance.now() - startedAt;
    clearTimeout(timeout);

    expect(response.status).toBe(200);
    expect(elapsedMs).toBeLessThanOrEqual(REQUEST_TIMEOUT_MS);
    expect(elapsedMs).toBeLessThanOrEqual(RECOMMENDED_LATENCY_MS);

    const payload = (await response.json()) as CockpitHomeBffResponse;
    expect(payload).toMatchObject({
      ok: true,
      source_label_taxonomy_version: 'source_label_semantics_v1',
    });
    expect(typeof payload.generated_at).toBe('string');
    expect(['READY', 'PARTIAL', 'DEGRADED', 'DATA_MISSING']).toContain(payload.data_state);
    expect(typeof payload.degraded).toBe('boolean');
    expect(Array.isArray(payload.data_missing)).toBe(true);

    expect(payload.market_session).toBeTruthy();
    expect(payload.portfolio).toBeTruthy();
    expect(Array.isArray(payload.market_movers)).toBe(true);
    expect(Array.isArray(payload.news)).toBe(true);
    expect(payload.attention_queue_state).toBeTruthy();
    expect(Array.isArray(payload.attention_queue)).toBe(true);
    expect(Array.isArray(payload.data_health)).toBe(true);
    expect(payload.narrative).toBeTruthy();

    expect(payload.portfolio.source_label).toBe('local_personal_data');
    expect(payload.data_health.map((item) => item.section)).toEqual(
      expect.arrayContaining([
        'data_health',
        'market_session',
        'portfolio',
        'news',
        'attention_queue',
        'market_movers',
        'session_summary',
      ]),
    );

    if (payload.data_state === 'PARTIAL') {
      expect(payload.data_missing.length).toBeGreaterThan(0);
    }
    if (!payload.degraded && payload.data_state !== 'READY') {
      expect(payload.data_missing.length).toBeGreaterThan(0);
    }

    assertMissingIfEmpty(payload.news.length, payload.data_missing, 'news');
    assertMissingIfEmpty(payload.market_movers.length, payload.data_missing, 'market_movers');
    assertMissingIfEmpty(payload.narrative.session_summary, payload.narrative.data_missing, 'session_summary');
    assertMissingIfEmpty(payload.narrative.theme_candidates.length, payload.narrative.data_missing, 'theme_candidates');
    assertMissingIfEmpty(payload.narrative.tomorrow_prep.length, payload.narrative.data_missing, 'tomorrow_prep');

    for (const signal of payload.data_missing) {
      expect(signal.source_label).not.toBe('claim_verified');
      expect(signal.source_label).not.toBe('financial_truth');
    }
    assertUnresolvedItemsDoNotLookSourceBacked(payload.news);
    assertUnresolvedItemsDoNotLookSourceBacked(payload.market_movers);
    assertUnresolvedItemsDoNotLookSourceBacked(payload.attention_queue);
  });
});

function assertMissingIfEmpty(
  value: number | string | null,
  dataMissing: CockpitHomeDataMissingSignal[],
  section: CockpitHomeDataMissingSignal['section'],
) {
  if (typeof value === 'number' ? value > 0 : Boolean(value)) {
    return;
  }

  expect(dataMissing.map((signal) => signal.section)).toContain(section);
}

function assertUnresolvedItemsDoNotLookSourceBacked(items: CockpitHomeSourceBearingItem[]) {
  for (const item of items) {
    assertStateCarriesMissingReasons(item.state);
    if (item.evidence.resolvable && item.state.data_state === 'READY') {
      continue;
    }
    expect(item.evidence.source_label).not.toBe('claim_verified');
    expect(item.evidence.source_label).not.toBe('financial_truth');
    expect(item.evidence.evidence_labels).not.toContain('claim_verified');
    expect(item.evidence.evidence_labels).not.toContain('financial_truth');
  }
}

function assertStateCarriesMissingReasons(state: CockpitHomeDeterministicState) {
  if (state.data_state === 'PARTIAL' || state.data_state === 'DATA_MISSING') {
    expect(state.data_missing.length).toBeGreaterThan(0);
  }
}
