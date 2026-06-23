const DEFAULT_BACKEND_URL = 'http://localhost:8000'
const BODYLESS_RESPONSE_STATUSES = new Set([204, 205, 304])

export type ProxyFetch = (input: string, init?: RequestInit) => Promise<Response>

export type ProxyBackendRequestOptions = {
  path: string
  method?: string
  forwardBody?: boolean
  fetcher?: ProxyFetch
}

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

export function resolveBackendPath(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${resolveBackendUrl()}${normalizedPath}`
}

export async function buildBackendResponse(backend: Response): Promise<Response> {
  const payload = await backend.text()
  const body = BODYLESS_RESPONSE_STATUSES.has(backend.status) ? null : payload
  return new Response(body, {
    status: backend.status,
    headers: {
      'Content-Type': backend.headers.get('Content-Type') ?? 'application/json',
    },
  })
}

export async function proxyBackendRequest(
  request: Request,
  options: ProxyBackendRequestOptions,
): Promise<Response> {
  const init: RequestInit = {
    headers: copyRequestHeaders(request),
    cache: 'no-store',
  }

  if (options.method) {
    init.method = options.method
  }
  if (options.forwardBody) {
    init.body = await request.text()
  }

  const fetcher = options.fetcher ?? fetch
  const backend = await fetcher(resolveBackendPath(options.path), init)
  return buildBackendResponse(backend)
}
