export interface MarketplaceMission {
  mission_id: string
  name: string
  status: string
  mission_type: string
  brief: string
  user_goal?: string | null
  category_hint: string | null
  hard_filters: Record<string, unknown>
  soft_preferences: Record<string, unknown>
  search_config: Record<string, unknown>
  scan_config: Record<string, unknown>
  benchmark_sources?: string[]
  deployment_args?: Record<string, unknown>
  last_error?: string | null
  created_from_chat_message_id?: string | null
  created_at: string
  updated_at: string
  last_scan_at: string | null
  requirement_profile?: MarketplaceRequirementProfile | null
  candidate_products?: MarketplaceCandidateProduct[]
  primary_tracked_product?: MarketplacePrimaryTrackedProductLink | null
  benchmark_state?: MarketplaceBenchmarkState | null
}

export interface MarketplaceRequirementProfile {
  mode: string
  category?: string | null
  intended_use?: string | null
  budget?: Record<string, unknown> | null
  local_area?: string | null
  hard_constraints?: Array<Record<string, unknown>>
  soft_preferences?: Array<Record<string, unknown>>
  performance_tier_hints?: string[]
  exact_product_hint?: string | null
  extracted_terms?: string[]
  unsupported_reason?: string | null
}

export interface MarketplaceCandidateProduct {
  mission_id: string
  tracked_product_id: string
  candidate_key: string
  category: string
  candidate_rank: number
  fit_score: number
  fit_label: string
  hard_constraints_met: string[]
  soft_preferences_met: string[]
  explanation?: string | null
  created_at: string
  updated_at: string
  tracked_product?: MarketplaceTrackedProduct | null
  benchmark_state?: MarketplaceBenchmarkState | null
  warning?: string | null
}

export interface MarketplaceTrackedProduct {
  tracked_product_id: string
  canonical_key: string
  category: string
  brand?: string | null
  model_family?: string | null
  variant?: string | null
  attributes: Record<string, unknown>
  aliases: string[]
  negative_terms: string[]
  status: string
  created_at: string
  updated_at: string
}

export interface MarketplacePrimaryTrackedProductLink {
  mission_id: string
  tracked_product_id: string
  link_type: string
  created_at: string
  updated_at: string
  tracked_product?: MarketplaceTrackedProduct | null
  warning?: string | null
}

export interface MarketplaceBenchmarkState {
  status: string
  freshness_status: string
  confidence_label: string
  sample_size: number
  snapshot_id?: string | null
  generated_at?: string | null
  fair_low?: number | null
  fair_high?: number | null
  used_median?: number | null
  retail_anchor_price?: number | null
  warnings?: string[]
  notes?: string[]
}

export interface MarketplaceBrowserHealth {
  status: string
  cdp_url: string
  browser_family: string
  profile_path: string
  challenge_detected: boolean
  last_checked_at: string
  detail?: string | null
  final_url?: string | null
}

export interface MarketplaceScanJob {
  job_id: string
  action_id: string
  mission_id?: string | null
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
  listing_media?: string[]
  status: string
  metadata: Record<string, unknown>
  benchmark?: MarketplaceBenchmarkOverlay | null
  value_context?: MarketplaceValueContext | null
  updated_at: string
}

export interface MarketplaceValueContext {
  state: string
  value_score?: number | null
  value_label: string
  value_confidence: string
  benchmark_snapshot_id?: string | null
  fair_low?: number | null
  fair_high?: number | null
  used_median?: number | null
  retail_anchor_price?: number | null
  price_movement_summary?: string | null
  explanation?: string | null
  warnings?: string[]
  notes?: string[]
  linked_tracked_product_id?: string | null
  linked_tracked_product_name?: string | null
  benchmark_freshness_status?: string | null
  benchmark_sample_size?: number | null
  variant_match_confidence?: number | null
  condition_certainty?: string | null
  mission_mode?: string | null
  value_source?: string | null
  matched_candidate_tracked_product_id?: string | null
  matched_candidate_name?: string | null
  candidate_match_confidence?: number | null
  requirement_fit_score?: number | null
  requirement_fit_label?: string | null
  requirement_explanation?: string | null
  requirement_category?: string | null
  computed_at?: string | null
}

export interface MarketplaceBenchmarkOverlay {
  source: string
  category: string
  matched_product: string | null
  current_price: number | null
  median_30d: number | null
  listing_delta_pct: number | null
  freshness_hours: number | null
  confidence: number
  low_confidence: boolean
  review_status: string
  warning: string | null
  rationale: string[]
  wording: string
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

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
  timeoutMs = 10_000,
): Promise<Response> {
  const controller = new AbortController()
  const timer = globalThis.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.ceil(timeoutMs / 1000)}s`)
    }
    throw error
  } finally {
    globalThis.clearTimeout(timer)
  }
}

export async function getMarketplaceBrowserHealth(apiKey: string): Promise<MarketplaceBrowserHealth> {
  const response = await fetchWithTimeout('/api/cockpit/marketplace/browser-health', {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  }, 8_000)
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

export async function listMarketplaceTrackedProducts(
  apiKey: string,
): Promise<MarketplaceTrackedProduct[]> {
  const response = await fetch('/api/cockpit/marketplace/price-intelligence/tracked-products', {
    headers: buildHeaders(apiKey, null),
    cache: 'no-store',
  })
  const body = await parseJson<{ items: MarketplaceTrackedProduct[] }>(response)
  return body.items
}

export async function linkMarketplaceMissionTrackedProduct(
  apiKey: string,
  missionId: string,
  trackedProductId: string,
): Promise<MarketplaceMission> {
  const response = await fetch(
    `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}/link-product`,
    {
      method: 'POST',
      headers: buildHeaders(apiKey),
      body: JSON.stringify({ tracked_product_id: trackedProductId }),
    },
  )
  return parseJson<MarketplaceMission>(response)
}

export async function unlinkMarketplaceMissionTrackedProduct(
  apiKey: string,
  missionId: string,
): Promise<MarketplaceMission> {
  const response = await fetch(
    `/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}/link-product`,
    {
      method: 'DELETE',
      headers: buildHeaders(apiKey, null),
    },
  )
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

export async function deleteMarketplaceMission(
  apiKey: string,
  missionId: string,
): Promise<{
  ok: boolean
  mission_id: string
  status: string
  deleted_missions: number
  deleted_seen_listings: number
  deleted_matches: number
  deleted_alerts: number
  deleted_listing_product_matches: number
  deleted_listing_benchmark_scores: number
  deleted_mission_product_links: number
  deleted_match_value_assessments: number
}> {
  const response = await fetch(`/api/cockpit/marketplace/missions/${encodeURIComponent(missionId)}`, {
    method: 'DELETE',
    headers: buildHeaders(apiKey, null),
  })
  return parseJson<{
    ok: boolean
    mission_id: string
    status: string
    deleted_missions: number
    deleted_seen_listings: number
    deleted_matches: number
    deleted_alerts: number
    deleted_listing_product_matches: number
    deleted_listing_benchmark_scores: number
    deleted_mission_product_links: number
    deleted_match_value_assessments: number
  }>(response)
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
  tail = 500,
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

export async function stopMarketplaceScanJob(
  apiKey: string,
  jobId: string,
): Promise<{ ok: boolean; job_id: string; status: string }> {
  const response = await fetch(`/api/cockpit/action/jobs/${encodeURIComponent(jobId)}/stop`, {
    method: 'POST',
    headers: buildHeaders(apiKey, null),
  })
  return parseJson<{ ok: boolean; job_id: string; status: string }>(response)
}

export async function triggerMarketplaceScan(
  apiKey: string,
  missionId?: string,
): Promise<MarketplaceScanJob> {
  const response = await fetchWithTimeout('/api/cockpit/marketplace/scans', {
    method: 'POST',
    headers: buildHeaders(apiKey),
    body: JSON.stringify({ mission_id: missionId || null }),
  }, 12_000)
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

export async function reviewMarketplaceBenchmarkMatch(
  apiKey: string,
  matchId: string,
  payload: { review_status: string; note?: string | null },
): Promise<MarketplaceMatch> {
  const response = await fetch(
    `/api/cockpit/marketplace/matches/${encodeURIComponent(matchId)}/benchmark-review`,
    {
      method: 'PATCH',
      headers: buildHeaders(apiKey),
      body: JSON.stringify(payload),
    },
  )
  return parseJson<MarketplaceMatch>(response)
}

export async function refreshMarketplaceBenchmarks(
  apiKey: string,
): Promise<{
  ok: boolean
  retailer: string
  observed_at: string
  canonical_created: number
  retailer_products_created: number
  price_observations_added: number
  live_observations_added?: number
  fallback_observations_added?: number
  fetch_failures?: string[]
  categories: string[]
}> {
  const response = await fetch('/api/cockpit/marketplace/benchmarks/refresh', {
    method: 'POST',
    headers: buildHeaders(apiKey, null),
  })
  return parseJson<{
    ok: boolean
    retailer: string
    observed_at: string
    canonical_created: number
    retailer_products_created: number
    price_observations_added: number
    live_observations_added?: number
    fallback_observations_added?: number
    fetch_failures?: string[]
    categories: string[]
  }>(response)
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
