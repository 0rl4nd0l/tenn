export interface MarketplaceMission {
  mission_id: string
  name: string
  status: string
  brief: string
  category_hint: string | null
  hard_filters: Record<string, unknown>
  soft_preferences: Record<string, unknown>
  search_config: Record<string, unknown>
  scan_config: Record<string, unknown>
  created_at: string
  updated_at: string
  last_scan_at: string | null
}

export interface MarketplaceBrowserHealth {
  status: string
  cdp_url: string
  browser_family: string
  profile_path: string
  logged_in: boolean
  challenge_detected: boolean
  last_checked_at: string
  detail?: string | null
  final_url?: string | null
}

export interface MarketplaceScanJob {
  job_id: string
  action_id: string
  status: string
  started_at?: string | null
  ended_at?: string | null
  exit_code?: number | null
  stdout_path?: string | null
  stderr_path?: string | null
  result?: string | null
  progress_stage?: string | null
  progress_pct?: number | null
}

export interface MarketplaceMatch {
  match_id: string
  mission_id: string
  mission_name?: string | null
  listing_id: string
  listing_url: string
  title: string
  price?: string | null
  price_value?: number | null
  location?: string | null
  seller_name?: string | null
  captured_at: string
  score: number
  decision_band: string
  reasons_for: string[]
  reasons_against: string[]
  confidence?: number | null
  raw_text_snapshot: string
  screenshot_path?: string | null
  status: string
  metadata: Record<string, unknown>
  updated_at: string
}

export interface MarketplaceAlert {
  alert_id: string
  mission_id: string
  mission_name?: string | null
  match_id: string
  match_title?: string | null
  listing_url?: string | null
  price?: string | null
  location?: string | null
  decision_band?: string | null
  status: string
  created_at: string
  updated_at: string
  trigger_reason: string
  metadata: Record<string, unknown>
}

function buildHeaders(apiKey: string, contentType: string | null = 'application/json'): HeadersInit {
  const headers: Record<string, string> = {}
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  if (contentType) {
    headers['Content-Type'] = contentType
  }
  return headers
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body?.detail) {
        detail = body.detail
      }
    } catch {
      try {
        detail = await response.text()
      } catch {
        detail = `${response.status}`
      }
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export async function getMarketplaceBrowserHealth(apiKey: string): Promise<MarketplaceBrowserHealth> {
  const response = await fetch('/api/cockpit/marketplace/browser-health', {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  return parseJson<MarketplaceBrowserHealth>(response)
}

export async function launchMarketplaceBrowser(apiKey: string): Promise<{ result: string }> {
  const response = await fetch('/api/cockpit/action/execute', {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify({
      action_id: 'launch_marketplace_browser',
      args: {},
      wait: true,
    }),
  })
  return parseJson<{ result: string }>(response)
}

export async function listMarketplaceMissions(
  apiKey: string,
  status?: string,
): Promise<MarketplaceMission[]> {
  const params = new URLSearchParams()
  if (status) {
    params.set('status', status)
  }
  const suffix = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`/api/cockpit/marketplace/missions${suffix}`, {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  const body = await parseJson<{ items: MarketplaceMission[] }>(response)
  return body.items
}

export async function createMarketplaceMission(
  apiKey: string,
  payload: Record<string, unknown>,
): Promise<MarketplaceMission> {
  const response = await fetch('/api/cockpit/marketplace/missions', {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify(payload),
  })
  return parseJson<MarketplaceMission>(response)
}

export async function updateMarketplaceMission(
  apiKey: string,
  missionId: string,
  payload: Record<string, unknown>,
): Promise<MarketplaceMission> {
  const response = await fetch(`/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`, {
    method: 'PATCH',
    headers: buildHeaders(apiKey),
    body: JSON.stringify(payload),
  })
  return parseJson<MarketplaceMission>(response)
}

export async function listMarketplaceScanJobs(apiKey: string): Promise<MarketplaceScanJob[]> {
  const response = await fetch('/api/cockpit/marketplace/scans', {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  const body = await parseJson<{ items: MarketplaceScanJob[] }>(response)
  return body.items
}

export async function getMarketplaceScanJob(
  apiKey: string,
  jobId: string,
  tail = 80,
): Promise<MarketplaceScanJob> {
  const response = await fetch(
    `/api/cockpit/marketplace/scans/${encodeURIComponent(jobId)}?tail=${tail}`,
    {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
    },
  )
  return parseJson<MarketplaceScanJob>(response)
}

export async function triggerMarketplaceScan(
  apiKey: string,
  missionId?: string,
): Promise<MarketplaceScanJob> {
  const response = await fetch('/api/cockpit/marketplace/scans', {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify({ mission_id: missionId || null }),
  })
  return parseJson<MarketplaceScanJob>(response)
}

export async function listMarketplaceMatches(
  apiKey: string,
  filters?: { missionId?: string; status?: string; decisionBand?: string },
): Promise<MarketplaceMatch[]> {
  const params = new URLSearchParams()
  if (filters?.missionId) params.set('mission_id', filters.missionId)
  if (filters?.status) params.set('status', filters.status)
  if (filters?.decisionBand) params.set('decision_band', filters.decisionBand)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`/api/cockpit/marketplace/matches${suffix}`, {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  const body = await parseJson<{ items: MarketplaceMatch[] }>(response)
  return body.items
}

export async function getMarketplaceMatch(apiKey: string, matchId: string): Promise<MarketplaceMatch> {
  const response = await fetch(`/api/cockpit/marketplace/matches/${encodeURIComponent(matchId)}`, {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  return parseJson<MarketplaceMatch>(response)
}

export async function updateMarketplaceMatch(
  apiKey: string,
  matchId: string,
  status: string,
): Promise<MarketplaceMatch> {
  const response = await fetch(`/api/cockpit/marketplace/matches/${encodeURIComponent(matchId)}`, {
    method: 'PATCH',
    headers: buildHeaders(apiKey),
    body: JSON.stringify({ status }),
  })
  return parseJson<MarketplaceMatch>(response)
}

export async function listMarketplaceAlerts(
  apiKey: string,
  status?: string,
): Promise<MarketplaceAlert[]> {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`/api/cockpit/marketplace/alerts${suffix}`, {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  const body = await parseJson<{ items: MarketplaceAlert[] }>(response)
  return body.items
}

export async function updateMarketplaceAlert(
  apiKey: string,
  alertId: string,
  status: string,
): Promise<MarketplaceAlert> {
  const response = await fetch(`/api/cockpit/marketplace/alerts/${encodeURIComponent(alertId)}`, {
    method: 'PATCH',
    headers: buildHeaders(apiKey),
    body: JSON.stringify({ status }),
  })
  return parseJson<MarketplaceAlert>(response)
}
