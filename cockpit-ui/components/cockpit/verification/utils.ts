import type {
  ExtractionEvidenceQuality,
  ExtractionMethod,
  ExtractionReviewItem,
  ExtractionReviewSession,
  VerificationContextResponse,
  VerificationResult,
} from '@/lib/cockpit-types'

import { DEFAULT_VERIFICATION_TAB } from './constants'
import type { ActiveExtractionMonitorRun, VerificationTab } from './types'

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatRawValue(value: unknown): string | number {
  if (typeof value === 'number') return value
  if (typeof value === 'string') return value
  if (value == null) return '-'
  return String(value)
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    : []
}

function mapVerificationContextResponse(data: VerificationContextResponse): VerificationResult[] | null {
  if (
    !Array.isArray(data.extraction_failures)
    && !Array.isArray(data.low_confidence_financials)
    && !Array.isArray(data.errors)
  ) {
    return null
  }

  const results: VerificationResult[] = []

  for (const failure of asRecordArray(data.extraction_failures)) {
    const documentId = formatRawValue(failure.document_id)
    const status = formatRawValue(failure.status ?? 'failed')
    const error = formatRawValue(failure.error)
    const ticker = formatRawValue(failure.ticker)
    const title = formatRawValue(failure.title)
    results.push({
      metric: 'Extraction failure',
      expected: 'status ok',
      actual: status,
      passed: false,
      details: [ticker, title, error].filter((value) => value !== '-').join(' | ') || 'Failed extraction run',
      document_id: typeof failure.document_id === 'string' ? failure.document_id : undefined,
    })
    if (documentId !== '-' && !results[results.length - 1].details?.includes(String(documentId))) {
      results[results.length - 1].details = `${results[results.length - 1].details} | ${documentId}`
    }
  }

  for (const row of asRecordArray(data.low_confidence_financials)) {
    const confidence = formatRawValue(row.confidence_metrics)
    const ticker = formatRawValue(row.ticker)
    const periodType = formatRawValue(row.period_type)
    const periodEnd = formatRawValue(row.period_end)
    results.push({
      metric: 'Low confidence financials',
      expected: 'confidence >= threshold',
      actual: confidence,
      passed: false,
      details: [ticker, periodType, periodEnd].filter((value) => value !== '-').join(' | ') || 'Low confidence financial row',
      document_id: typeof row.source_document_id === 'string' ? row.source_document_id : undefined,
    })
  }

  for (const error of data.errors || []) {
    results.push({
      metric: 'Verification error',
      expected: 'backend query ok',
      actual: String(error),
      passed: false,
      details: String(error),
    })
  }

  if (results.length === 0) {
    results.push({
      metric: 'Backend verification context',
      expected: 'no failures or low-confidence rows',
      actual: 'clear',
      passed: true,
      details: 'No extraction failures, low-confidence financial rows, or verification errors returned.',
    })
  }

  return results
}

export function mapResponseToResults(data: unknown): VerificationResult[] {
  if (!data || typeof data !== 'object') {
    return [{
      metric: 'Raw Response',
      expected: '-',
      actual: String(data),
      passed: false,
      details: 'Unexpected response format',
    }]
  }

  const verificationResults = mapVerificationContextResponse(data as VerificationContextResponse)
  if (verificationResults) return verificationResults

  const items = Array.isArray(data)
    ? data
    : 'metrics' in data && Array.isArray((data as Record<string, unknown>).metrics)
      ? (data as Record<string, unknown>).metrics as unknown[]
      : null

  if (!items) {
    return [{
      metric: 'Raw Response',
      expected: '-',
      actual: JSON.stringify(data, null, 2),
      passed: false,
      details: 'Unrecognized response shape',
    }]
  }

  return items.map((item: unknown, index: number) => {
    if (!item || typeof item !== 'object') {
      return { metric: `Check ${index + 1}`, expected: '-', actual: String(item), passed: false }
    }

    const record = item as Record<string, unknown>
    return {
      metric: String(record.metric ?? record.name ?? record.label ?? `Check ${index + 1}`),
      expected: formatRawValue(record.expected),
      actual: formatRawValue(record.actual ?? record.value),
      passed: typeof record.passed === 'boolean' ? record.passed : (record.status === 'pass' || record.status === 'ok'),
      details: record.details ? String(record.details) : undefined,
      document_id: record.document_id ? String(record.document_id) : (record.doc_id ? String(record.doc_id) : undefined),
      item_id: record.item_id ? String(record.item_id) : (record.id ? String(record.id) : undefined),
    }
  })
}

export function formatValue(value: string | number): string {
  if (typeof value !== 'number') return value
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
  return value.toLocaleString()
}

export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function parseDocumentIds(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  )
}

export function isReviewableExtractionStatus(status: string): boolean {
  return status === 'ok' || status === 'ok_low_confidence' || status === 'parser_error'
}

export function statusVariant(status: ExtractionReviewItem['review_status']): 'default' | 'secondary' | 'critical' | 'outline' {
  if (status === 'approved') return 'default'
  if (status === 'wrong') return 'critical'
  if (status === 'abstain') return 'secondary'
  return 'outline'
}

export function reviewStatusLabel(status: ExtractionReviewItem['review_status']): string {
  if (status === 'approved') return 'correct'
  if (status === 'abstain') return 'unsure'
  return status
}

export function formatMethodLabel(method: string | ExtractionMethod | null | undefined): string {
  const normalized = String(method || '').trim()
  if (!normalized) return 'unknown'
  if (normalized === 'pymupdf') return 'PyMuPDF'
  if (normalized === 'pymupdf_degraded') return 'PyMuPDF degraded'
  return normalized
}

export function evidenceMethodLabel(item: ExtractionReviewItem | null): string {
  if (!item) return 'unknown'
  return formatMethodLabel(item.method_provenance || item.actual_method || item.requested_method)
}

export function summarizeSessionDocuments(session: ExtractionReviewSession | null): string {
  if (!session?.documents || session.documents.length === 0) {
    return 'No review session diagnostics available yet.'
  }

  return session.documents
    .map((doc) => {
      const label = doc.title || doc.document_id
      const status = doc.status || 'unknown'
      const count = typeof doc.items_count === 'number' ? doc.items_count : 0
      const reason = doc.reason ? `, ${doc.reason}` : ''
      const metrics = typeof doc.metrics_count === 'number' ? `, metrics ${doc.metrics_count}` : ''
      return `${label}: ${status}${count > 0 ? ` (${count} item${count === 1 ? '' : 's'})` : ''}${metrics}${reason}`
    })
    .join(' | ')
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function formatDuration(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`
  return `${value}ms`
}

export function normalizeEvidenceText(value: string | null | undefined): string | null {
  const text = String(value || '').trim()
  if (!text || text.toLowerCase() === 'unknown') return null
  return text
}

export function evidenceQualityForItem(item: ExtractionReviewItem | null): ExtractionEvidenceQuality {
  if (!item) return 'missing'
  const explicit = item.evidence_quality || item.snippet.evidence_quality
  if (explicit === 'precise' || explicit === 'approximate' || explicit === 'missing') {
    return explicit
  }

  const hasImage = Boolean(item.image_url || item.image_path || item.snippet.image_url || item.snippet.image_path)
  const matchedText = normalizeEvidenceText(item.matched_text)
    || normalizeEvidenceText(item.snippet.matched_text)
    || normalizeEvidenceText(item.evidence_text)

  if (hasImage && item.snippet.kind === 'line_crop' && matchedText) return 'precise'
  if (hasImage) return 'approximate'
  return 'missing'
}

export function evidenceQualityRank(quality: ExtractionEvidenceQuality): number {
  if (quality === 'precise') return 0
  if (quality === 'approximate') return 1
  return 2
}

export function evidenceQualityBadgeVariant(quality: ExtractionEvidenceQuality): 'default' | 'secondary' | 'outline' {
  if (quality === 'precise') return 'default'
  if (quality === 'approximate') return 'secondary'
  return 'outline'
}

export function evidenceQualityLabel(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'precise'
  if (quality === 'approximate') return 'approximate'
  return 'missing'
}

export function evidenceQualityHeadline(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'Source Page with Highlighting'
  if (quality === 'approximate') return 'Full Source Page'
  return 'No visual verification evidence available'
}

export function evidenceQualityBody(quality: ExtractionEvidenceQuality): string {
  if (quality === 'precise') return 'This metric includes the full source page with the extracted line highlighted.'
  if (quality === 'approximate') return 'Showing the full source page for context. Verify using the provenance details.'
  return 'No snippet image was preserved for visual verification. Use provenance details only.'
}

export function reviewSessionRunIds(session: ExtractionReviewSession | null): string[] {
  if (!session) return []
  const explicit = Array.isArray(session.run_ids)
    ? session.run_ids.filter((runId): runId is string => Boolean(runId))
    : []
  const fallback = session.items
    .map((item) => item.run_id)
    .filter((runId): runId is string => Boolean(runId))
  return Array.from(new Set([...explicit, ...fallback]))
}

function readMonitorString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function readMonitorNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function readMonitorBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

export function parseActiveExtractionMonitorRuns(payload: Record<string, unknown>): ActiveExtractionMonitorRun[] {
  const rawRuns = payload.extraction_active_runs
  if (!Array.isArray(rawRuns)) return []

  return rawRuns.flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return []
    const run = entry as Record<string, unknown>
    const runId = readMonitorString(run.run_id)
    const documentId = readMonitorString(run.document_id)
    if (!runId || !documentId) return []

    return [{
      runId,
      documentId,
      requestedMethod: readMonitorString(run.requested_method),
      strictMethod: readMonitorBoolean(run.strict_method),
      ticker: readMonitorString(run.ticker),
      title: readMonitorString(run.title),
      expiresInSeconds: readMonitorNumber(run.expires_in_seconds),
    }]
  })
}

export function runStatusVariant(status: string | null | undefined): 'default' | 'secondary' | 'critical' | 'outline' {
  if (status === 'succeeded') return 'default'
  if (status === 'failed' || status === 'blocked') return 'critical'
  if (status === 'running') return 'secondary'
  return 'outline'
}

export function parseVerificationTab(value: string | null | undefined): VerificationTab {
  if (value === 'review' || value === 'gold-eval' || value === 'runs' || value === 'verify') {
    return value
  }
  return DEFAULT_VERIFICATION_TAB
}

export function isKeyboardShortcutBlocked(target: EventTarget | null): boolean {
  const element = target instanceof HTMLElement ? target : null
  if (!element) return false

  if (element.isContentEditable) return true

  const tagName = element.tagName.toLowerCase()
  if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
    return true
  }

  return Boolean(element.closest('[contenteditable="true"], [role="combobox"], [data-slot="select-trigger"]'))
}
