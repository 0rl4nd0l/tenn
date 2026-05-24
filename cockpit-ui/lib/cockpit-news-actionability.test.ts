import { describe, expect, it } from 'vitest'

import {
  getNewsReadiness,
  getNewsResultReadiness,
  type NewsActionabilityResult,
} from './cockpit-news-actionability'

const now = new Date('2026-05-24T00:00:00.000Z')

describe('Cockpit News actionability helpers', () => {
  it('does not treat an empty query as usable news context', () => {
    expect(getNewsReadiness({
      query: '',
      isSearching: false,
      searchError: null,
      results: null,
      now,
    })).toMatchObject({
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
    })
  })

  it('keeps search failures degraded instead of falling through to empty results', () => {
    expect(getNewsReadiness({
      query: 'CSL price trend',
      isSearching: false,
      searchError: '503 backend unavailable',
      results: [],
      now,
    })).toMatchObject({
      reason: 'DEGRADED',
      label: 'DEGRADED',
    })
  })

  it('marks missing published_at as DATA_MISSING and does not call it fresh', () => {
    const results = [
      newsResult({ publishedAtMissing: true, date: new Date(0) }),
      newsResult({ id: 'with-date', headline: 'CSL filing notice', url: 'https://example.com/csl' }),
    ]

    expect(getNewsReadiness({
      query: 'CSL filing',
      isSearching: false,
      searchError: null,
      results,
      now,
    })).toMatchObject({
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
    })
    expect(getNewsResultReadiness(results[0], results, now)).toMatchObject({
      reason: 'DATA_MISSING',
      label: 'DATE MISSING',
    })
  })

  it('clusters repeated results without upgrading them to verified evidence', () => {
    const results = [
      newsResult({ id: 'a', url: 'https://example.com/notice#top' }),
      newsResult({ id: 'b', url: 'https://example.com/notice' }),
    ]

    const readiness = getNewsReadiness({
      query: 'CSL filings',
      isSearching: false,
      searchError: null,
      results,
      now,
    })

    expect(readiness).toMatchObject({
      reason: 'DUPLICATED',
      label: 'DUPLICATED',
    })
    expect(readiness.detail).toContain('one evidence cluster')
    expect(getNewsResultReadiness(results[0], results, now)).toMatchObject({
      reason: 'DUPLICATED',
      label: 'DUPLICATE x2',
    })
  })

  it('does not hide DATA_MISSING behind duplicate badges', () => {
    const results = [
      newsResult({ id: 'a', url: 'https://example.com/notice', publishedAtMissing: true, date: new Date(0) }),
      newsResult({ id: 'b', url: 'https://example.com/notice', publishedAtMissing: true, date: new Date(0) }),
    ]

    expect(getNewsResultReadiness(results[0], results, now)).toMatchObject({
      reason: 'DATA_MISSING',
      label: 'DATE MISSING',
      duplicateCount: 2,
    })
  })
})

function newsResult(overrides: Partial<NewsActionabilityResult> = {}): NewsActionabilityResult {
  return {
    id: 'news-a',
    headline: 'CSL filing notice',
    source: 'asx',
    date: new Date('2026-05-23T00:00:00.000Z'),
    relevanceScore: 0.91,
    ticker: 'CSL',
    content: 'Filing context only.',
    url: 'https://example.com/csl-filing',
    ...overrides,
  }
}
