'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CheckCircle2, XCircle, Loader2, AlertTriangle, Zap, Server, Database, Brain, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ServiceCheck {
  name: string
  icon: React.ReactNode
  status: 'checking' | 'healthy' | 'degraded' | 'down' | 'unknown'
  required: boolean
  endpoint: string
  responseTimeMs?: number
  error?: string
}

interface HealthCheckConfig {
  /** URL to fetch for the health check */
  url: string
  /** If true, this is a cross-origin request that may fail due to CORS */
  crossOrigin: boolean
  /** Optional custom response parser for non-trivial health payloads */
  parseResponse?: (response: Response, body: unknown) => { ok: boolean; error?: string }
}

const serviceConfigs: Record<string, HealthCheckConfig | null> = {
  'Backend API': {
    url: '/api/cockpit/health',
    crossOrigin: false,
    parseResponse: (_response, body) => {
      const services = Array.isArray((body as { services?: unknown[] } | null)?.services)
        ? (body as { services: Array<{ name?: string; status?: string }> }).services
        : []
      const backend = services.find((service) => service.name === 'backend')
      const ok = backend?.status === 'healthy'
      return { ok, error: ok ? undefined : backend?.status ?? 'backend not healthy' }
    },
  },
  'llama.cpp': { url: 'http://localhost:8001/health', crossOrigin: true },
  'Ollama Embeddings': { url: 'http://localhost:11434/api/tags', crossOrigin: true },
  'Qdrant': { url: 'http://localhost:6333/healthz', crossOrigin: true },
  'Redis': null, // Cannot be checked from browser
}

const initialServices: ServiceCheck[] = [
  { name: 'Backend API', icon: <Server className="h-4 w-4" />, status: 'checking', required: true, endpoint: '/api/cockpit/health' },
  { name: 'llama.cpp', icon: <Brain className="h-4 w-4" />, status: 'checking', required: true, endpoint: 'http://localhost:8001' },
  { name: 'Ollama Embeddings', icon: <Brain className="h-4 w-4" />, status: 'checking', required: true, endpoint: 'http://localhost:11434' },
  { name: 'Qdrant', icon: <Search className="h-4 w-4" />, status: 'checking', required: false, endpoint: 'http://localhost:6333' },
  { name: 'Redis', icon: <Database className="h-4 w-4" />, status: 'checking', required: false, endpoint: 'http://localhost:6379' },
]

function getStatusIcon(status: ServiceCheck['status']) {
  switch (status) {
    case 'healthy':
      return <CheckCircle2 className="h-5 w-5 text-[oklch(0.65_0.2_145)]" />
    case 'degraded':
      return <AlertTriangle className="h-5 w-5 text-[oklch(0.75_0.15_80)]" />
    case 'down':
      return <XCircle className="h-5 w-5 text-[oklch(0.55_0.2_25)]" />
    case 'unknown':
      return <AlertTriangle className="h-5 w-5 text-muted-foreground" />
    default:
      return <Loader2 className="h-5 w-5 text-primary animate-spin" />
  }
}

export function BootScreen() {
  const router = useRouter()
  const [services, setServices] = useState<ServiceCheck[]>(initialServices)
  const [profile, setProfile] = useState('full')
  const [isBooting, setIsBooting] = useState(true)
  const [progress, setProgress] = useState(0)

  // Real service health checks
  useEffect(() => {
    const controllers: AbortController[] = []
    let completed = 0
    const total = initialServices.length

    const checkService = async (index: number) => {
      const service = initialServices[index]
      const config = serviceConfigs[service.name]

      // Redis cannot be checked from the browser
      if (config === null) {
        setServices(prev => {
          const next = [...prev]
          next[index] = { ...next[index], status: 'unknown', error: 'Not checkable from browser' }
          return next
        })
        completed++
        setProgress((completed / total) * 100)
        if (completed === total) setIsBooting(false)
        return
      }

      const controller = new AbortController()
      controllers.push(controller)
      const start = performance.now()

      // Abort after 5 seconds
      const timeoutId = setTimeout(() => controller.abort(), 5000)

      try {
        const response = await fetch(config.url, {
          method: 'GET',
          signal: controller.signal,
        })
        clearTimeout(timeoutId)
        const elapsed = Math.round(performance.now() - start)

        let parsedBody: unknown = null
        try {
          parsedBody = await response.json()
        } catch {
          parsedBody = null
        }

        const parsed = config.parseResponse?.(response, parsedBody)
        const serviceOk = parsed ? parsed.ok : response.ok

        if (serviceOk) {
          setServices(prev => {
            const next = [...prev]
            next[index] = { ...next[index], status: 'healthy', responseTimeMs: elapsed }
            return next
          })
        } else {
          setServices(prev => {
            const next = [...prev]
            next[index] = {
              ...next[index],
              status: 'down',
              responseTimeMs: elapsed,
              error: parsed?.error ?? `HTTP ${response.status}`,
            }
            return next
          })
        }
      } catch (err: unknown) {
        clearTimeout(timeoutId)
        const elapsed = Math.round(performance.now() - start)
        const isCorsOrNetwork = err instanceof TypeError

        if (config.crossOrigin && isCorsOrNetwork) {
          // Cross-origin fetch failures are likely CORS, not necessarily down
          setServices(prev => {
            const next = [...prev]
            next[index] = {
              ...next[index],
              status: 'unknown',
              responseTimeMs: elapsed,
              error: 'CORS or network error',
            }
            return next
          })
        } else {
          const message =
            err instanceof DOMException && err.name === 'AbortError'
              ? 'Timeout (5s)'
              : err instanceof Error
                ? err.message
                : 'Connection failed'
          setServices(prev => {
            const next = [...prev]
            next[index] = {
              ...next[index],
              status: 'down',
              responseTimeMs: elapsed,
              error: message,
            }
            return next
          })
        }
      } finally {
        completed++
        setProgress((completed / total) * 100)
        if (completed === total) {
          setIsBooting(false)
        }
      }
    }

    // Check all services in parallel
    initialServices.forEach((_, i) => checkService(i))

    return () => controllers.forEach(c => c.abort())
  }, [])

  const requiredHealthy = services.filter(s => s.required && s.status === 'healthy').length
  const requiredDown = services.filter(s => s.required && s.status === 'down').length
  const requiredTotal = services.filter(s => s.required).length
  const allRequiredHealthy = requiredDown === 0 && !services.some(s => s.required && s.status === 'checking')

  const handleLaunch = () => {
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-primary">
            <Zap className="h-8 w-8 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">Financial Cockpit</CardTitle>
          <CardDescription>
            {isBooting ? 'Checking service health...' : 'Service check complete'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Progress */}
          {isBooting && (
            <div className="space-y-2">
              <Progress value={progress} />
              <p className="text-xs text-center text-muted-foreground">
                Checking services... {Math.round(progress)}%
              </p>
            </div>
          )}

          {/* Service List */}
          <div className="space-y-3">
            {services.map((service) => (
              <div 
                key={service.name}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg border',
                  service.status === 'checking' && 'border-border bg-muted/30',
                  service.status === 'healthy' && 'border-[oklch(0.65_0.2_145)]/30 bg-[oklch(0.65_0.2_145)]/5',
                  service.status === 'degraded' && 'border-[oklch(0.75_0.15_80)]/30 bg-[oklch(0.75_0.15_80)]/5',
                  service.status === 'down' && 'border-[oklch(0.55_0.2_25)]/30 bg-[oklch(0.55_0.2_25)]/5',
                  service.status === 'unknown' && 'border-border bg-muted/20',
                )}
              >
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground">{service.icon}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{service.name}</span>
                      {!service.required && (
                        <Badge variant="outline" className="text-[9px]">Optional</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground font-mono">{service.endpoint}</p>
                    {service.error && (
                      <p className="text-xs text-[oklch(0.55_0.2_25)] mt-0.5">{service.error}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {service.responseTimeMs && (
                    <span className="text-xs text-muted-foreground font-mono">
                      {service.responseTimeMs}ms
                    </span>
                  )}
                  {getStatusIcon(service.status)}
                </div>
              </div>
            ))}
          </div>

          {/* CORS notice */}
          {!isBooting && services.some(s => s.status === 'unknown') && (
            <p className="text-xs text-muted-foreground text-center">
              Direct health checks may be blocked by CORS. Use /health command for full status.
            </p>
          )}

          {/* Profile Selector */}
          {!isBooting && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Launch Profile</label>
              <Select value={profile} onValueChange={setProfile}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">Full (All features)</SelectItem>
                  <SelectItem value="isolated">Isolated (Local only)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Status Summary */}
          {!isBooting && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Required services: {requiredHealthy}/{requiredTotal}
              </span>
              <Badge variant={allRequiredHealthy ? 'default' : 'destructive'}>
                {allRequiredHealthy ? 'Ready' : 'Issues Detected'}
              </Badge>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button 
              className="flex-1" 
              onClick={handleLaunch}
              disabled={isBooting}
            >
              <Zap className="h-4 w-4 mr-2" />
              {allRequiredHealthy ? 'Launch Cockpit' : 'Launch Anyway'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
