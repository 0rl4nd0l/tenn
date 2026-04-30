export function toReportDisplayPath(rawPath: string | null | undefined): string {
  const value = String(rawPath || '').trim()
  if (!value) return ''

  const normalized = value.replace(/\\/g, '/')
  const marker = '/reports/'
  const markerIndex = normalized.indexOf(marker)
  if (markerIndex >= 0) {
    return normalized.slice(markerIndex + 1)
  }
  if (normalized.startsWith('reports/')) {
    return normalized
  }
  return value
}

