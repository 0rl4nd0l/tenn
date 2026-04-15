'use client'

type ConsoleLevel = 'error' | 'warn'

type ConsoleEntry = {
  level: ConsoleLevel
  timestamp: string
  message: string
}

type RuntimeErrorEntry = {
  timestamp: string
  type: 'error' | 'unhandledrejection'
  message: string
  source?: string | null
  lineno?: number | null
  colno?: number | null
  stack?: string | null
}

type NetworkEntry = {
  timestamp: string
  url: string
  method: string
  status?: number | null
  ok?: boolean | null
  duration_ms?: number | null
  error?: string | null
}

type ResourceTimingEntry = {
  name: string
  initiatorType: string
  startTime: number
  duration: number
  transferSize?: number
  encodedBodySize?: number
  decodedBodySize?: number
}

export type BrowserDebugSnapshot = {
  collected_at: string
  page: {
    href: string
    pathname: string
    search: string
    title: string
    referrer: string
  }
  viewport: {
    width: number
    height: number
    devicePixelRatio: number
  }
  navigator: {
    userAgent: string
    language: string
    platform: string
    online: boolean
    cookieEnabled: boolean
    timezone: string
  }
  performance: {
    timeOrigin: number
    navigation: Record<string, unknown> | null
    memory: Record<string, unknown> | null
    resources: ResourceTimingEntry[]
  }
  dom: {
    documentReadyState: string
    nodeCount: number
    imageCount: number
    iframeCount: number
  }
  console: ConsoleEntry[]
  runtime_errors: RuntimeErrorEntry[]
  network: NetworkEntry[]
}

const MAX_CONSOLE = 40
const MAX_ERRORS = 30
const MAX_NETWORK = 60
const MAX_RESOURCES = 30

type Store = {
  installed: boolean
  console: ConsoleEntry[]
  runtimeErrors: RuntimeErrorEntry[]
  network: NetworkEntry[]
}

const store: Store = {
  installed: false,
  console: [],
  runtimeErrors: [],
  network: [],
}

function pushBounded<T>(items: T[], item: T, limit: number): void {
  items.push(item)
  if (items.length > limit) {
    items.splice(0, items.length - limit)
  }
}

function stringifyArgs(args: unknown[]): string {
  return args
    .map((value) => {
      if (value instanceof Error) {
        return value.stack || value.message || String(value)
      }
      if (typeof value === 'string') {
        return value
      }
      try {
        return JSON.stringify(value)
      } catch {
        return String(value)
      }
    })
    .join(' ')
    .trim()
}

function installConsoleCollector(): void {
  for (const level of ['error', 'warn'] as const) {
    const current = console[level]
    const marker = `__cockpit_debug_wrapped_${level}`
    if ((current as unknown as { [key: string]: unknown })?.[marker]) {
      continue
    }

    const wrapped = (...args: unknown[]) => {
      pushBounded(
        store.console,
        {
          level,
          timestamp: new Date().toISOString(),
          message: stringifyArgs(args),
        },
        MAX_CONSOLE,
      )
      current(...args)
    }
    ;(wrapped as unknown as { [key: string]: unknown })[marker] = true
    console[level] = wrapped as typeof console[typeof level]
  }
}

function installRuntimeErrorCollector(): void {
  window.addEventListener(
    'error',
    (event) => {
      pushBounded(
        store.runtimeErrors,
        {
          timestamp: new Date().toISOString(),
          type: 'error',
          message: event.message || 'Unknown browser error',
          source: event.filename || null,
          lineno: event.lineno || null,
          colno: event.colno || null,
          stack: event.error instanceof Error ? event.error.stack || null : null,
        },
        MAX_ERRORS,
      )
    },
    true,
  )

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    pushBounded(
      store.runtimeErrors,
      {
        timestamp: new Date().toISOString(),
        type: 'unhandledrejection',
        message:
          reason instanceof Error
            ? reason.message
            : typeof reason === 'string'
              ? reason
              : stringifyArgs([reason]),
        stack: reason instanceof Error ? reason.stack || null : null,
      },
      MAX_ERRORS,
    )
  })
}

function installFetchCollector(): void {
  const windowWithFetch = window as typeof window & {
    __cockpitDebugFetchWrapped?: boolean
  }
  if (windowWithFetch.__cockpitDebugFetchWrapped) {
    return
  }

  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const startedAt = performance.now()
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url
    const method = String(init?.method || (input instanceof Request ? input.method : 'GET') || 'GET').toUpperCase()

    try {
      const response = await originalFetch(input, init)
      pushBounded(
        store.network,
        {
          timestamp: new Date().toISOString(),
          url,
          method,
          status: response.status,
          ok: response.ok,
          duration_ms: Number((performance.now() - startedAt).toFixed(2)),
        },
        MAX_NETWORK,
      )
      return response
    } catch (error) {
      pushBounded(
        store.network,
        {
          timestamp: new Date().toISOString(),
          url,
          method,
          duration_ms: Number((performance.now() - startedAt).toFixed(2)),
          error: error instanceof Error ? error.message : String(error),
        },
        MAX_NETWORK,
      )
      throw error
    }
  }

  windowWithFetch.__cockpitDebugFetchWrapped = true
}

function getNavigationSnapshot(): Record<string, unknown> | null {
  const [entry] = performance.getEntriesByType('navigation')
  if (!(entry instanceof PerformanceNavigationTiming)) {
    return null
  }
  return {
    type: entry.type,
    startTime: entry.startTime,
    duration: entry.duration,
    domContentLoadedEventEnd: entry.domContentLoadedEventEnd,
    loadEventEnd: entry.loadEventEnd,
    transferSize: entry.transferSize,
    encodedBodySize: entry.encodedBodySize,
    decodedBodySize: entry.decodedBodySize,
  }
}

function getMemorySnapshot(): Record<string, unknown> | null {
  const perfWithMemory = performance as Performance & {
    memory?: {
      jsHeapSizeLimit?: number
      totalJSHeapSize?: number
      usedJSHeapSize?: number
    }
  }
  if (!perfWithMemory.memory) {
    return null
  }
  return {
    jsHeapSizeLimit: perfWithMemory.memory.jsHeapSizeLimit ?? null,
    totalJSHeapSize: perfWithMemory.memory.totalJSHeapSize ?? null,
    usedJSHeapSize: perfWithMemory.memory.usedJSHeapSize ?? null,
  }
}

function getResourceSnapshot(): ResourceTimingEntry[] {
  return performance
    .getEntriesByType('resource')
    .slice(-MAX_RESOURCES)
    .map((entry) => {
      const resourceEntry = entry as PerformanceResourceTiming
      return {
        name: resourceEntry.name,
        initiatorType: resourceEntry.initiatorType,
        startTime: Number(resourceEntry.startTime.toFixed(2)),
        duration: Number(resourceEntry.duration.toFixed(2)),
        transferSize: resourceEntry.transferSize,
        encodedBodySize: resourceEntry.encodedBodySize,
        decodedBodySize: resourceEntry.decodedBodySize,
      }
    })
}

export function installBrowserDebugCollector(): void {
  if (typeof window === 'undefined' || store.installed) {
    return
  }
  installConsoleCollector()
  installRuntimeErrorCollector()
  installFetchCollector()
  store.installed = true
}

export function getBrowserDebugSnapshot(): BrowserDebugSnapshot {
  if (typeof window === 'undefined') {
    return {
      collected_at: new Date().toISOString(),
      page: {
        href: '',
        pathname: '',
        search: '',
        title: '',
        referrer: '',
      },
      viewport: {
        width: 0,
        height: 0,
        devicePixelRatio: 1,
      },
      navigator: {
        userAgent: '',
        language: '',
        platform: '',
        online: false,
        cookieEnabled: false,
        timezone: '',
      },
      performance: {
        timeOrigin: 0,
        navigation: null,
        memory: null,
        resources: [],
      },
      dom: {
        documentReadyState: 'unknown',
        nodeCount: 0,
        imageCount: 0,
        iframeCount: 0,
      },
      console: [],
      runtime_errors: [],
      network: [],
    }
  }

  const doc = window.document
  return {
    collected_at: new Date().toISOString(),
    page: {
      href: window.location.href,
      pathname: window.location.pathname,
      search: window.location.search,
      title: doc.title,
      referrer: doc.referrer,
    },
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio || 1,
    },
    navigator: {
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      online: navigator.onLine,
      cookieEnabled: navigator.cookieEnabled,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    },
    performance: {
      timeOrigin: performance.timeOrigin,
      navigation: getNavigationSnapshot(),
      memory: getMemorySnapshot(),
      resources: getResourceSnapshot(),
    },
    dom: {
      documentReadyState: doc.readyState,
      nodeCount: doc.getElementsByTagName('*').length,
      imageCount: doc.images.length,
      iframeCount: doc.getElementsByTagName('iframe').length,
    },
    console: [...store.console],
    runtime_errors: [...store.runtimeErrors],
    network: [...store.network],
  }
}
