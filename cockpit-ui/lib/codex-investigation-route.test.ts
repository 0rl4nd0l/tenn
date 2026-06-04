import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { POST as deployCodexInvestigation } from '@/app/api/cockpit/feedback/flags/[reportId]/deploy/route'
import { GET as getCodexInvestigation } from '@/app/api/cockpit/feedback/flags/[reportId]/investigation/route'
import { POST as deployLocalCodexInvestigation } from '@/app/cockpit-local/feedback/flags/[reportId]/deploy/route'

const deployIntentHeaders = {
  'X-Cockpit-Control-Intent': 'deploy-codex-investigation',
}

const readIntentHeaders = {
  'X-Cockpit-Control-Intent': 'read-codex-investigation',
}

const spawnMock = vi.hoisted(() => vi.fn(() => ({
  pid: 12345,
  once: vi.fn(),
  unref: vi.fn(),
})))

vi.mock('node:child_process', () => ({
  default: {
    spawn: spawnMock,
  },
  spawn: spawnMock,
}))

function createQueuedReport(reportId = 'flag_20260430_abc123', status = 'queued'): {
  workspace: string
  reportId: string
  reportDir: string
} {
  const workspace = mkdtempSync(path.join(os.tmpdir(), 'cockpit-codex-route-'))
  const reportDir = path.join(
    workspace,
    'reports',
    'cockpit',
    'flagged_sessions',
    'session-1',
    reportId,
  )
  mkdirSync(reportDir, { recursive: true })
  writeFileSync(path.join(reportDir, 'codex_prompt.md'), 'Investigate this flag.\n')
  writeFileSync(
    path.join(reportDir, 'investigation.json'),
    JSON.stringify({
      report_id: reportId,
      status,
      mode: 'operator_gated_codex_cli',
      codex_prompt_path: path.join(reportDir, 'codex_prompt.md'),
      updated_at: '2026-04-30T00:00:00Z',
    }),
  )
  return { workspace, reportId, reportDir }
}

describe('Codex investigation deploy route', () => {
  afterEach(() => {
    delete process.env.COCKPIT_WORKSPACE_ROOT
    delete process.env.COCKPIT_CODEX_RUNNER_PYTHON
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('rejects missing deploy intent before resolving local artifacts or spawning', async () => {
    process.env.COCKPIT_WORKSPACE_ROOT = path.join(os.tmpdir(), 'missing-cockpit-workspace')
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await deployCodexInvestigation(
      new Request('http://localhost/api/cockpit/feedback/flags/flag_20260430_abc123/deploy', {
        method: 'POST',
      }),
      { params: Promise.resolve({ reportId: '../bad' }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'codex_investigation_deploy_intent_required',
    })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('rejects wrong deploy intent before resolving local artifacts or spawning', async () => {
    process.env.COCKPIT_WORKSPACE_ROOT = path.join(os.tmpdir(), 'missing-cockpit-workspace')
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await deployCodexInvestigation(
      new Request('http://localhost/api/cockpit/feedback/flags/flag_20260430_abc123/deploy', {
        method: 'POST',
        headers: {
          'X-Cockpit-Control-Intent': 'read-codex-investigation',
        },
      }),
      { params: Promise.resolve({ reportId: 'flag_20260430_abc123' }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'codex_investigation_deploy_intent_required',
    })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('applies the same deploy guard through the cockpit-local alias', async () => {
    process.env.COCKPIT_WORKSPACE_ROOT = path.join(os.tmpdir(), 'missing-cockpit-workspace')

    const response = await deployLocalCodexInvestigation(
      new Request('http://localhost/cockpit-local/feedback/flags/flag_20260430_abc123/deploy', {
        method: 'POST',
      }),
      { params: Promise.resolve({ reportId: 'flag_20260430_abc123' }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'codex_investigation_deploy_intent_required',
    })
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('rejects non-loopback deploy requests before spawning', async () => {
    const { workspace, reportId } = createQueuedReport()
    process.env.COCKPIT_WORKSPACE_ROOT = workspace
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await deployCodexInvestigation(
      new Request(`http://192.168.1.10/api/cockpit/feedback/flags/${reportId}/deploy`, {
        method: 'POST',
        headers: {
          ...deployIntentHeaders,
          host: '192.168.1.10',
        },
      }),
      { params: Promise.resolve({ reportId }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'non_loopback_codex_investigation_deploy_denied',
    })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('rejects cross-origin deploy requests before spawning', async () => {
    const { workspace, reportId } = createQueuedReport()
    process.env.COCKPIT_WORKSPACE_ROOT = workspace
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await deployCodexInvestigation(
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/deploy`, {
        method: 'POST',
        headers: {
          ...deployIntentHeaders,
          origin: 'https://example.invalid',
          'sec-fetch-site': 'cross-site',
        },
      }),
      { params: Promise.resolve({ reportId }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'cross_origin_codex_investigation_deploy_denied',
    })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('starts the local runner for an existing queued report', async () => {
    const { workspace, reportId } = createQueuedReport()
    process.env.COCKPIT_WORKSPACE_ROOT = workspace
    const fetchMock = vi.fn(async () => new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const response = await deployCodexInvestigation(
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/deploy`, {
        method: 'POST',
        headers: deployIntentHeaders,
      }),
      { params: Promise.resolve({ reportId }) },
    )

    expect(response.status).toBe(202)
    expect(await response.json()).toMatchObject({
      ok: true,
      report_id: reportId,
      status: 'launching',
      pid: 12345,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/api/cockpit/feedback/flags/${reportId}`,
      expect.objectContaining({ cache: 'no-store' }),
    )
    expect(spawnMock).toHaveBeenCalledWith(
      'python3',
      expect.arrayContaining([
        path.resolve(process.cwd(), '..', 'scripts', 'cockpit_flag_investigator.py'),
        '--report-id',
        reportId,
        '--once',
        '--apply',
      ]),
      expect.objectContaining({
        cwd: path.resolve(process.cwd(), '..'),
        detached: true,
        stdio: 'ignore',
      }),
    )
  })

  it('allows retrying a failed report with force', async () => {
    const { workspace, reportId } = createQueuedReport('flag_20260430_retry123', 'failed')
    process.env.COCKPIT_WORKSPACE_ROOT = workspace
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200 })))

    const response = await deployCodexInvestigation(
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/deploy`, {
        method: 'POST',
        headers: deployIntentHeaders,
      }),
      { params: Promise.resolve({ reportId }) },
    )

    expect(response.status).toBe(202)
    expect(spawnMock).toHaveBeenCalledWith(
      'python3',
      expect.arrayContaining([
        '--report-id',
        reportId,
        '--apply',
        '--force',
      ]),
      expect.any(Object),
    )
  })
})

describe('Codex investigation status route', () => {
  afterEach(() => {
    delete process.env.COCKPIT_WORKSPACE_ROOT
    vi.clearAllMocks()
  })

  it('rejects missing read intent before resolving local artifacts', async () => {
    process.env.COCKPIT_WORKSPACE_ROOT = path.join(os.tmpdir(), 'missing-cockpit-workspace')

    const response = await getCodexInvestigation(
      new Request('http://localhost/api/cockpit/feedback/flags/flag_20260430_abc123/investigation'),
      { params: Promise.resolve({ reportId: '../bad' }) },
    )

    expect(response.status).toBe(403)
    expect(await response.json()).toMatchObject({
      ok: false,
      code: 'codex_investigation_read_intent_required',
    })
  })

  it('returns the stored investigation status and output tail', async () => {
    const { workspace, reportId, reportDir } = createQueuedReport()
    process.env.COCKPIT_WORKSPACE_ROOT = workspace
    const outputPath = path.join(reportDir, 'codex-last-message.md')
    writeFileSync(outputPath, 'Final Codex summary')
    writeFileSync(
      path.join(reportDir, 'investigation.json'),
      JSON.stringify({
        report_id: reportId,
        status: 'completed',
        codex_prompt_path: path.join(reportDir, 'codex_prompt.md'),
        codex_output_path: outputPath,
        returncode: 0,
      }),
    )

    const response = await getCodexInvestigation(
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/investigation`, {
        headers: readIntentHeaders,
      }),
      { params: Promise.resolve({ reportId }) },
    )

    expect(response.status).toBe(200)
    expect(await response.json()).toMatchObject({
      ok: true,
      report_id: reportId,
      status: 'completed',
      returncode: 0,
      output_tail: 'Final Codex summary',
    })
  })
})
