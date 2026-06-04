import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const SCRIPT_PATH = fileURLToPath(import.meta.url)
const SCRIPT_DIR = path.dirname(SCRIPT_PATH)

export const REQUIRED_SOURCE_FILES = [
  'cockpit-ui/app/page.tsx',
  'cockpit-ui/components/cockpit/chat/chat-screen.tsx',
  'cockpit-ui/lib/cockpit-chat-actionability.ts',
]

export const REQUIRED_ROUTE_PAIRS = [
  {
    frontendRoute: '/api/cockpit/config',
    localSource: 'cockpit-ui/app/api/cockpit/config/route.ts',
    backendDecorator: '/config',
  },
  {
    frontendRoute: '/api/cockpit/health',
    localSource: 'cockpit-ui/app/api/cockpit/health/route.ts',
    backendDecorator: '/health',
  },
  {
    frontendRoute: '/api/cockpit/holdings',
    localSource: 'cockpit-ui/app/api/cockpit/holdings/route.ts',
    backendDecorator: '/holdings',
  },
  {
    frontendRoute: '/api/cockpit/watchlist',
    localSource: 'cockpit-ui/app/api/cockpit/watchlist/route.ts',
    backendDecorator: '/watchlist',
  },
]

const BACKEND_ROUTE_FILES = [
  'financial-engine_v2/backend/app/api/routes.py',
  'financial-engine_v2/backend/app/routes/cockpit_api.py',
]
const NEXT_CONFIG_PATH = 'cockpit-ui/next.config.mjs'

function defaultRepoRoot() {
  return path.resolve(SCRIPT_DIR, '..', '..')
}

function routeDecoratorPattern(route) {
  return new RegExp(`@router\\.(?:get|post|put|patch|delete)\\((['"])${route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\1`)
}

function hasGlobalApiRewrite(repoRoot) {
  const nextConfigPath = path.join(repoRoot, NEXT_CONFIG_PATH)
  if (!existsSync(nextConfigPath)) {
    return false
  }
  const nextConfigText = readFileSync(nextConfigPath, 'utf8')
  return /source:\s*['"]\/api\/:path\*['"]/.test(nextConfigText)
    && /destination:\s*`?\$\{backendUrl\}\/api\/:path\*`?/.test(nextConfigText)
}

export function collectRouteSurfaceIssues(repoRoot = defaultRepoRoot()) {
  const issues = []

  for (const relativePath of REQUIRED_SOURCE_FILES) {
    if (!existsSync(path.join(repoRoot, relativePath))) {
      issues.push({
        type: 'missing_source',
        path: relativePath,
      })
    }
  }

  const backendTexts = BACKEND_ROUTE_FILES.map((relativePath) => {
    const absolutePath = path.join(repoRoot, relativePath)
    return existsSync(absolutePath) ? readFileSync(absolutePath, 'utf8') : ''
  })
  const globalApiRewrite = hasGlobalApiRewrite(repoRoot)

  for (const pair of REQUIRED_ROUTE_PAIRS) {
    const hasLocalSource = existsSync(path.join(repoRoot, pair.localSource))
    if (!hasLocalSource && !globalApiRewrite) {
      issues.push({
        type: 'missing_frontend_route_coverage',
        frontendRoute: pair.frontendRoute,
        localSource: pair.localSource,
      })
      continue
    }

    const backendRouteExists = backendTexts.some((text) => routeDecoratorPattern(pair.backendDecorator).test(text))
    if (!backendRouteExists) {
      issues.push({
        type: 'missing_backend_route',
        frontendRoute: pair.frontendRoute,
        backendDecorator: pair.backendDecorator,
      })
    }
  }

  return issues
}

export function runRouteSurfaceCheck(repoRoot = defaultRepoRoot()) {
  const issues = collectRouteSurfaceIssues(repoRoot)
  if (issues.length > 0) {
    return {
      ok: false,
      issues,
      checked: {
        sourceFiles: REQUIRED_SOURCE_FILES.length,
        routePairs: REQUIRED_ROUTE_PAIRS.length,
      },
    }
  }

  return {
    ok: true,
    checked: {
      sourceFiles: REQUIRED_SOURCE_FILES.length,
      routePairs: REQUIRED_ROUTE_PAIRS.length,
    },
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH) {
  const result = runRouteSurfaceCheck()
  if (!result.ok) {
    console.error(JSON.stringify(result, null, 2))
    process.exit(1)
  }
  console.log(JSON.stringify(result))
}
