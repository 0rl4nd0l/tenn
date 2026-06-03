import { getCockpitConfig } from '@/lib/config'

export default function SettingsPage() {
  const config = getCockpitConfig()
  return <main><h1>Settings</h1><pre>{JSON.stringify(config, null, 2)}</pre></main>
}
