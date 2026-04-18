const DEFAULT_BACKEND_URL = 'http://localhost:8000'

export function resolveBackendUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_BACKEND_URL).replace(/\/$/, '')
}

export function copyRequestHeaders(request: Request | Headers): Headers {
  const source = request instanceof Headers ? request : request.headers
  const copied = new Headers()
  source.forEach((value, key) => {
    const normalized = key.toLowerCase()
    if (normalized === 'host' || normalized === 'content-length') {
      return
    }
    copied.set(key, value)
  })
  return copied
}
