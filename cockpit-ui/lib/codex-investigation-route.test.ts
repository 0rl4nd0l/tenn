import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { spawn } from 'node:child_process'
import { POST as deployCodexInvestigation } from '@/app/api/cockpit/feedback/flags/[reportId]/deploy/route'
import { GET as getCodexInvestigation } from '@/app/api/cockpit/feedback/flags/[reportId]/investigation/route'

vi.mock('node:child_process', () => ({
  default: {
    spawn: vi.fn(() => ({
      pid: 12345,
      once: vi.fn(),
      unref: vi.fn(),
    })),
  },
  spawn: vi.fn(() => ({
    pid: 12345,
    once: vi.fn(),
    unref: vi.fn(),
  })),
}))

function createQueuedReport(reportId = 'flag_20260430_abc123'): {
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
      status: 'queued',
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
  })

  it('starts the local runner for an existing queued report', async () => {
    const { workspace, reportId } = createQueuedReport()
    process.env.COCKPIT_WORKSPACE_ROOT = workspace

    const response = await deployCodexInvestigation(
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/deploy`, {
        method: 'POST',
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
    expect(spawn).toHaveBeenCalledWith(
      'python3',
      expect.arrayContaining([
        'scripts/cockpit_flag_investigator.py',
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
})

describe('Codex investigation status route', () => {
  afterEach(() => {
    delete process.env.COCKPIT_WORKSPACE_ROOT
    vi.clearAllMocks()
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
      new Request(`http://localhost/api/cockpit/feedback/flags/${reportId}/investigation`),
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
