import { describe, expect, it } from 'vitest';

import {
  buildCockpitHomeChatHandoff,
  cockpitHomeHasDataMissing,
  cockpitHomeIsDegraded,
  cockpitHomeSourceLabelToTrustLevel,
  collectCockpitHomeStateIssues,
  normalizeCockpitHomeSourceLabel,
} from './cockpit-home-contract';
import type { CockpitHomeSourceBearingItem } from '@/types/cockpit-home';

const readyState: CockpitHomeSourceBearingItem['state'] = {
  data_state: 'READY',
  degraded: false,
  data_missing: [],
  as_of: '2026-05-06T00:00:00Z',
};

const baseSourceItem: CockpitHomeSourceBearingItem = {
  id: 'home-news-1',
  section: 'news',
  title: 'BHP announces operational update',
  ticker: 'BHP',
  observed_at: '2026-05-06T00:00:00Z',
  state: readyState,
  evidence: {
    source_id: 'commentary:bhp-update',
    source_kind: 'ephemeral',
    source_label: 'local_news_context',
    evidence_labels: ['local_news_context', 'context_only'],
    resolvable: true,
    resolver: 'cockpit_chat_attached_sources',
    evidence_id: 'ev-bhp-update',
    document_id: null,
    chunk_id: 'commentary:bhp-update:0',
    url: null,
    title: 'BHP operational update',
    published_at: '2026-05-06T00:00:00Z',
  },
};

describe('Cockpit Home contract helpers', () => {
  it('maps backend snake_case evidence labels to Home display trust labels', () => {
    expect(cockpitHomeSourceLabelToTrustLevel('claim_verified')).toBe('CLAIM-VERIFIED');
    expect(cockpitHomeSourceLabelToTrustLevel('financial_truth')).toBe('FINANCIAL-TRUTH');
    expect(cockpitHomeSourceLabelToTrustLevel('missing_required_evidence')).toBe('MISSING-EVIDENCE');
    expect(cockpitHomeSourceLabelToTrustLevel('degraded_runtime')).toBe('DEGRADED-RUNTIME');
    expect(cockpitHomeSourceLabelToTrustLevel('not_in_taxonomy')).toBe('UNKNOWN-UNCLASSIFIED');
    expect(normalizeCockpitHomeSourceLabel(null)).toBe('unknown_unclassified');
  });

  it('does not upgrade context, no-hit, missing, or degraded labels to verified trust', () => {
    expect(cockpitHomeSourceLabelToTrustLevel('context_only')).toBe('CONTEXT-ONLY');
    expect(cockpitHomeSourceLabelToTrustLevel('no_hit')).toBe('NO-HIT');
    expect(cockpitHomeSourceLabelToTrustLevel('missing_required_evidence')).toBe('MISSING-EVIDENCE');
    expect(cockpitHomeSourceLabelToTrustLevel('degraded_runtime')).toBe('DEGRADED-RUNTIME');
  });

  it('keeps DATA_MISSING and degraded semantics explicit and deterministic', () => {
    expect(
      cockpitHomeHasDataMissing({
        data_state: 'READY',
        data_missing: [],
        evidence: { source_label: 'no_hit', evidence_labels: ['context_only', 'no_hit'] },
      }),
    ).toBe(true);
    expect(
      cockpitHomeIsDegraded({
        data_state: 'READY',
        degraded: false,
        evidence: { source_label: 'degraded_runtime', evidence_labels: ['degraded_runtime'] },
      }),
    ).toBe(true);
    expect(
      collectCockpitHomeStateIssues({
        data_state: 'DATA_MISSING',
        degraded: false,
        data_missing: [],
        as_of: null,
      }),
    ).toEqual([
      {
        section: 'data_health',
        code: 'DATA_MISSING_WITHOUT_REASON',
        message: 'DATA_MISSING state must carry at least one deterministic reason.',
      },
    ]);
  });

  it('builds a ChatScreen handoff only for backend-resolvable source identities', () => {
    expect(buildCockpitHomeChatHandoff(baseSourceItem, { initialPrompt: 'Analyse this item' })).toEqual({
      route: '/full-chat',
      chat_screen: 'ChatScreen',
      ticker: 'BHP',
      initial_prompt: 'Analyse this item',
      attached_sources: [
        {
          source_id: 'commentary:bhp-update',
          source_kind: 'ephemeral',
        },
      ],
    });

    const missingSource = {
      ...baseSourceItem,
      state: {
        data_state: 'DATA_MISSING',
        degraded: false,
        data_missing: [
          {
            section: 'news',
            code: 'NO_SOURCE_ID',
            message: 'Backend did not provide a resolvable source id.',
            source_label: 'missing_required_evidence',
          },
        ],
        as_of: null,
      },
      evidence: {
        ...baseSourceItem.evidence,
        source_id: null,
        source_label: 'missing_required_evidence',
        evidence_labels: ['missing_required_evidence', 'no_hit'],
        resolvable: false,
        resolver: 'none',
      },
    } satisfies CockpitHomeSourceBearingItem;

    expect(buildCockpitHomeChatHandoff(missingSource)).toEqual({
      route: '/full-chat',
      chat_screen: 'ChatScreen',
      ticker: 'BHP',
      attached_sources: [],
      blocked_reason: 'DATA_MISSING',
    });
  });
});
