export type CockpitConfig = {
  app: string
  mode: 'local'
  backendUrl: string
  apiKeyConfigured: boolean
  sourceStatus: 'restored-minimal-source'
  routes: string[]
}

export function getCockpitConfig(): CockpitConfig {
  return {
    app: 'TENN Cockpit',
    mode: 'local',
    backendUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    apiKeyConfigured: Boolean(process.env.TENN_API_KEY || process.env.API_KEY || process.env.NEXT_PUBLIC_TENN_API_KEY),
    sourceStatus: 'restored-minimal-source',
    routes: ['/api/cockpit/config', '/api/cockpit/health', '/api/cockpit/watchlist', '/api/cockpit/holdings']
  }
}
