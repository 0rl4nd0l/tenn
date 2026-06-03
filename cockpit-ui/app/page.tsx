import { getCockpitConfig } from '@/lib/config'

export default function HomePage() {
  const config = getCockpitConfig()
  return (
    <main>
      <h1>TENN Cockpit</h1>
      <p>Minimal restored source shell for the TENN local cockpit.</p>
      <section className="card">
        <h2>Backend</h2>
        <p><code>{config.backendUrl}</code></p>
        <p>API key configured: <strong>{String(config.apiKeyConfigured)}</strong></p>
      </section>
      <section className="card">
        <h2>Available local routes</h2>
        <ul>{config.routes.map((route) => <li key={route}><code>{route}</code></li>)}</ul>
      </section>
    </main>
  )
}
