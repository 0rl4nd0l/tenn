export type MarketplaceCaptureErrorKind =
  | 'browser_unavailable'
  | 'login_required'
  | 'other'

type MarketplaceCaptureError = {
  kind: MarketplaceCaptureErrorKind
  message: string
}

const BROWSER_UNAVAILABLE_PREFIX = 'marketplace_browser_unavailable:'
const LOGIN_REQUIRED_PREFIX = 'marketplace_login_required:'
const CAPTURE_FAILED_PREFIX = 'marketplace_capture_failed:'

function extractErrorDetail(rawBody: string, status: number): string {
  const trimmed = rawBody.trim()
  if (!trimmed) {
    return `Marketplace capture failed (${status})`
  }

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown; error?: unknown }
    const detail = typeof parsed?.detail === 'string'
      ? parsed.detail
      : typeof parsed?.error === 'string'
        ? parsed.error
        : ''
    if (detail.trim()) {
      return detail.trim()
    }
  } catch {
    // Ignore JSON parsing and fall back to the raw body text.
  }

  return trimmed
}

export function parseMarketplaceCaptureError(
  rawBody: string,
  status: number,
): MarketplaceCaptureError {
  const detail = extractErrorDetail(rawBody, status)

  if (detail.startsWith(BROWSER_UNAVAILABLE_PREFIX)) {
    return {
      kind: 'browser_unavailable',
      message: detail.slice(BROWSER_UNAVAILABLE_PREFIX.length).trim(),
    }
  }

  if (detail.startsWith(LOGIN_REQUIRED_PREFIX)) {
    return {
      kind: 'login_required',
      message: detail.slice(LOGIN_REQUIRED_PREFIX.length).trim(),
    }
  }

  if (detail.startsWith(CAPTURE_FAILED_PREFIX)) {
    return {
      kind: 'other',
      message: detail.slice(CAPTURE_FAILED_PREFIX.length).trim(),
    }
  }

  if (status === 503) {
    return { kind: 'browser_unavailable', message: detail }
  }

  if (status === 409) {
    return { kind: 'login_required', message: detail }
  }

  return { kind: 'other', message: detail }
}

export function shouldOfferMarketplaceBrowserLaunch(
  kind: MarketplaceCaptureErrorKind,
): boolean {
  return kind === 'browser_unavailable' || kind === 'login_required'
}
