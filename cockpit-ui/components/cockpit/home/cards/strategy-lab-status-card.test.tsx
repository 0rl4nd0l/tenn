import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  STRATEGY_LAB_BASELINE_REFS,
  VERIFIED_READONLY_SANDBOX_EVIDENCE_REFS,
  buildStrategyLabStatusResponse,
} from '@/lib/strategy-lab-status';
import { StrategyLabStatusCard } from './strategy-lab-status-card';

describe('StrategyLabStatusCard', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders pending-review status without implying live transport or trading', async () => {
    const payload = buildStrategyLabStatusResponse({
      generatedAt: '2026-05-24T00:00:00.000Z',
      artifactRefs: STRATEGY_LAB_BASELINE_REFS.map((ref) => ({
        ...ref,
        availability: 'available',
      })),
      verifiedReadonlySandboxEvidenceRefs: VERIFIED_READONLY_SANDBOX_EVIDENCE_REFS.map((ref) => ({
        ...ref,
        availability: 'available',
      })),
    });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    render(<StrategyLabStatusCard />);

    expect(await screen.findByText('PENDING REVIEW')).toBeInTheDocument();
    expect(screen.getByText('VERIFIED READ-ONLY SANDBOX PROOF')).toBeInTheDocument();
    expect(screen.getByText('Verified read-only sandbox proof available')).toBeInTheDocument();
    expect(screen.getByText('HISTORICAL SMOKE PASSED')).toBeInTheDocument();
    expect(screen.getAllByText('CURRENT SIDECAR OFFLINE').length).toBeGreaterThan(0);
    expect(screen.getByText('Strategy Lab / QuantDinger')).toBeInTheDocument();
    expect(screen.getByText('READ ONLY')).toBeInTheDocument();
    expect(screen.getByText('NO LIVE TRADING')).toBeInTheDocument();
    expect(screen.getByText('NO PAPER ORDERS')).toBeInTheDocument();
    expect(screen.getByText('NO REAL TRANSPORT')).toBeInTheDocument();
    expect(screen.getByText('NO STORE WRITES')).toBeInTheDocument();
    expect(screen.getByText('NO CANONICAL FINANCIAL TRUTH')).toBeInTheDocument();
    expect(screen.getByText('VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY')).toBeInTheDocument();
    expect(screen.getByText('current_sidecar_available:')).toBeInTheDocument();
    expect(screen.getAllByText('false').length).toBeGreaterThan(0);
    expect(screen.getByText('SMOKE_PASSED')).toBeInTheDocument();
    expect(screen.getByText('0ee837f7dc0706f1b0ff6d6c900522f4c2b43090')).toBeInTheDocument();
    expect(screen.getByText('stopped_after_cleanup')).toBeInTheDocument();
    expect(screen.getByText('10/10 available')).toBeInTheDocument();
    expect(screen.getByText('14/14 available')).toBeInTheDocument();
    expect(screen.getByText(/runtime_proof\.json/)).toBeInTheDocument();
    expect(screen.getByText(/zero_order_proof\.json/)).toBeInTheDocument();
    expect(screen.getByText('DATA_MISSING')).toBeInTheDocument();
    expect(screen.getByText(/No current QuantDinger sidecar capability/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/strategy-lab/status',
      expect.objectContaining({ cache: 'no-store' }),
    );
  });
});
