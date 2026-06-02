function configuredBrowserApiKey(): string {
  const envKey = process.env.NEXT_PUBLIC_API_KEY || ''
  if (typeof window === 'undefined') return envKey
  try {
    return window.localStorage.getItem('cockpit.apiKey') || envKey
  } catch {
    return envKey
  }
}

export function buildCockpitApiHeaders(headers?: HeadersInit): HeadersInit {
  const merged: Record<string, string> = {}
  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      merged[key] = value
    })
  } else if (Array.isArray(headers)) {
    for (const [key, value] of headers) {
      merged[key] = value
    }
  } else if (headers) {
    Object.assign(merged, headers)
  }
  const apiKey = configuredBrowserApiKey().trim()
  if (apiKey) {
    merged['X-API-Key'] = apiKey
  }
  return merged
}
