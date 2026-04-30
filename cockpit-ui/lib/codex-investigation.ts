import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'

const REPORT_ID_RE = /^[A-Za-z0-9_.-]{1,128}$/

export type CodexInvestigationRecord = {
  report_id?: string
  status?: string
  mode?: string
  codex_prompt_path?: string
  codex_prompt_relative_path?: string
  codex_events_path?: string
  codex_stderr_path?: string
  codex_output_path?: string
  suggested_command?: string | null
  codex_command?: string[]
  returncode?: number
  created_at?: string
  updated_at?: string
  started_at?: string
  completed_at?: string
  [key: string]: unknown
}

export type CodexInvestigationPaths = {
  repoRoot: string
  reportsRoot: string
  reportDir: string
  investigationPath: string
  promptPath: string
}

export function resolveRepoRoot(): string {
  return path.resolve(process.cwd(), '..')
}

export function resolveReportsRoot(repoRoot = resolveRepoRoot()): string {
  const workspace = String(process.env.COCKPIT_WORKSPACE_ROOT || '').trim()
  const base = workspace ? path.resolve(workspace) : repoRoot
  return path.resolve(base, 'reports', 'cockpit', 'flagged_sessions')
}

export function validateReportId(reportId: string): string {
  const normalized = String(reportId || '').trim()
  if (!REPORT_ID_RE.test(normalized)) {
    throw new Error('Invalid report_id')
  }
  return normalized
}

export function findReportDir(reportId: string, reportsRoot = resolveReportsRoot()): string {
  const normalized = validateReportId(reportId)
  if (!existsSync(reportsRoot)) {
    throw new Error(`Flagged report root not found: ${reportsRoot}`)
  }

  for (const sessionName of readdirSync(reportsRoot)) {
    const sessionDir = path.resolve(reportsRoot, sessionName)
    if (!sessionDir.startsWith(reportsRoot) || !statSync(sessionDir).isDirectory()) {
      continue
    }
    const candidate = path.resolve(sessionDir, normalized)
    if (
      candidate.startsWith(`${sessionDir}${path.sep}`)
      && existsSync(candidate)
      && statSync(candidate).isDirectory()
    ) {
      return candidate
    }
  }

  throw new Error(`Flagged report not found: ${normalized}`)
}

export function readInvestigation(reportDir: string): CodexInvestigationRecord {
  const investigationPath = path.resolve(reportDir, 'investigation.json')
  if (!existsSync(investigationPath)) {
    throw new Error(`Missing investigation.json for ${path.basename(reportDir)}`)
  }
  const parsed = JSON.parse(readFileSync(investigationPath, 'utf8')) as unknown
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`Invalid investigation.json for ${path.basename(reportDir)}`)
  }
  return parsed as CodexInvestigationRecord
}

export function resolvePromptPath(
  reportDir: string,
  investigation: CodexInvestigationRecord,
): string {
  const raw = String(investigation.codex_prompt_path || '').trim()
  if (raw) {
    const candidate = path.isAbsolute(raw) ? path.resolve(raw) : path.resolve(resolveRepoRoot(), raw)
    if (existsSync(candidate)) {
      return candidate
    }
  }
  const fallback = path.resolve(reportDir, 'codex_prompt.md')
  if (existsSync(fallback)) {
    return fallback
  }
  throw new Error(`Missing codex_prompt.md for ${path.basename(reportDir)}`)
}

export function resolveInvestigationPaths(reportId: string): CodexInvestigationPaths {
  const repoRoot = resolveRepoRoot()
  const reportsRoot = resolveReportsRoot(repoRoot)
  const reportDir = findReportDir(reportId, reportsRoot)
  const investigation = readInvestigation(reportDir)
  return {
    repoRoot,
    reportsRoot,
    reportDir,
    investigationPath: path.resolve(reportDir, 'investigation.json'),
    promptPath: resolvePromptPath(reportDir, investigation),
  }
}

export function readTail(filePath: string | undefined, maxChars = 4000): string | null {
  if (!filePath) {
    return null
  }
  const resolved = path.resolve(filePath)
  if (!existsSync(resolved)) {
    return null
  }
  const content = readFileSync(resolved, 'utf8')
  return content.length > maxChars ? content.slice(-maxChars) : content
}
