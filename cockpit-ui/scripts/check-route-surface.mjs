import { existsSync } from 'node:fs'

const required = [
  'app/api/cockpit/config/route.ts',
  'app/api/cockpit/health/route.ts',
  'app/api/cockpit/watchlist/route.ts',
  'app/api/cockpit/holdings/route.ts'
]

const missing = required.filter((path) => !existsSync(new URL(`../${path}`, import.meta.url)))
if (missing.length) {
  console.error('Missing Cockpit route source files:', missing)
  process.exit(1)
}
console.log(JSON.stringify({ ok: true, checked: required.length }))
