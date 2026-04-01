/** @type {import('next').NextConfig} */
const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const nextConfig = {
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
