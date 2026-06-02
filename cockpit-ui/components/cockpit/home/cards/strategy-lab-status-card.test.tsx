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
    delete process.env.NEXT_PUBLIC_API_KEY;
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
    process.env.NEXT_PUBLIC_API_KEY = 'operator-key';
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    render(<StrategyLabStatusCard />);

    expect(await screen.findByText('Read-only sandbox proof verified')).toBeInTheDocument();
    expect(screen.getAllByText(/Strategy Lab/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Offline').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pending review').length).toBeGreaterThan(0);
    expect(screen.getByText('Disabled')).toBeInTheDocument();
    expect(screen.getAllByText(/Repo-backed proof exists for read-only sandbox behavior/).length).toBeGreaterThan(0);
    expect(screen.getByText(/DATA_MISSING: No current QuantDinger sidecar capability/)).toBeInTheDocument();
    expect(screen.getByText('14/14 available')).toBeInTheDocument();
    expect(screen.getByText('10/10 available')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View details/i })).toHaveAttribute(
      'href',
      '#strategy-lab-artifacts-review-card',
    );
    expect(screen.getByRole('link', { name: /Open Strategy Lab/i })).toHaveAttribute(
      'href',
      '#strategy-lab-status-card',
    );
    expect(screen.queryByText('VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY')).not.toBeInTheDocument();
    expect(screen.queryByText('SMOKE_PASSED')).not.toBeInTheDocument();
    expect(screen.queryByText('0ee837f7dc0706f1b0ff6d6c900522f4c2b43090')).not.toBeInTheDocument();
    expect(screen.queryByText(/runtime_proof\.json/)).not.toBeInTheDocument();
    expect(screen.queryByText(/zero_order_proof\.json/)).not.toBeInTheDocument();
    expect(screen.queryByText('NO LIVE TRADING')).not.toBeInTheDocument();
    expect(screen.queryByText('NO STORE WRITES')).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/cockpit/strategy-lab/status',
      expect.objectContaining({
        cache: 'no-store',
        headers: expect.objectContaining({ 'X-API-Key': 'operator-key' }),
      }),
    );
  });
});
