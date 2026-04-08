import path from 'node:path'
import { fileURLToPath } from 'node:url'

/** @type {import('next').NextConfig} */
const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const configDir = path.dirname(fileURLToPath(import.meta.url))

const nextConfig = {
  outputFileTracingRoot: configDir,
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/research/:path*',
        destination: `${backendUrl}/research/:path*`,
      },
      {
        source: '/rag/:path*',
        destination: `${backendUrl}/rag/:path*`,
      },
    ]
  },
}

export default nextConfig
