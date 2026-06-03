export function backendHeaders(): HeadersInit {
  const key = process.env.TENN_API_KEY || process.env.API_KEY || process.env.NEXT_PUBLIC_TENN_API_KEY
  return key ? { 'X-API-Key': key } : {}
}
