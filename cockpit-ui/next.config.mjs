const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      { source: '/api/backend/:path*', destination: `${backendUrl}/api/:path*` },
      { source: '/rag/:path*', destination: `${backendUrl}/rag/:path*` },
      { source: '/research/:path*', destination: `${backendUrl}/research/:path*` }
    ]
  }
}

export default nextConfig
