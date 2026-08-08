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

type ServiceStatus = ServiceCheck['status']
type BffServiceStatus = Exclude<ServiceStatus, 'checking'>

interface BootServiceDefinition {
  name: string
  aliases: string[]
  icon: React.ReactNode
  required: boolean
}

interface BffServiceHealth {
  name?: unknown
  status?: unknown
  endpoint?: unknown
  response_time_ms?: unknown
  responseTimeMs?: unknown
  error?: unknown
}

const HEALTH_BFF_ENDPOINT = '/api/cockpit/health'

const serviceDefinitions: BootServiceDefinition[] = [
  {
    name: 'Backend API',
    aliases: ['backend'],
    icon: <Server className="h-4 w-4" />,
    required: true,
  },
  {
    name: 'llama.cpp',
    aliases: ['llamacpp', 'llama.cpp', 'llama_cpp'],
    icon: <Brain className="h-4 w-4" />,
    required: true,
  },
  {
    name: 'Ollama Embeddings',
    aliases: ['ollama', 'ollama_embeddings'],
    icon: <Brain className="h-4 w-4" />,
    required: true,
  },
  {
    name: 'Qdrant',
    aliases: ['qdrant'],
    icon: <Search className="h-4 w-4" />,
    required: false,
  },
  {
    name: 'Redis',
    aliases: ['redis'],
    icon: <Database className="h-4 w-4" />,
    required: false,
  },
  {
    name: 'GPU',
    aliases: ['gpu'],
    icon: <Zap className="h-4 w-4" />,
    required: false,
  },
  {
    name: 'Host',
    aliases: ['host'],
    icon: <Server className="h-4 w-4" />,
    required: false,
  },
]

function bffEndpointFor(definition: BootServiceDefinition): string {
  return `${HEALTH_BFF_ENDPOINT}#${definition.aliases[0]}`
}

function serviceFromDefinition(
  definition: BootServiceDefinition,
  status: ServiceStatus = 'checking',
): ServiceCheck {
  return {
    name: definition.name,
    icon: definition.icon,
    status,
    required: definition.required,
    endpoint: bffEndpointFor(definition),
  }
}

const initialServices: ServiceCheck[] = serviceDefinitions.map((definition) => (
  serviceFromDefinition(definition)
))

function normalizeServiceName(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase().replace(/[^a-z0-9]/g, '') : ''
}

function readString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

function readNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function readBffServices(body: unknown): BffServiceHealth[] {
  if (!body || typeof body !== 'object') return []
  const services = (body as { services?: unknown }).services
  if (!Array.isArray(services)) return []
  return services.filter((service): service is BffServiceHealth => (
    Boolean(service) && typeof service === 'object'
  ))
}

function coerceBffStatus(value: unknown): BffServiceStatus {
  if (
    value === 'healthy'
    || value === 'degraded'
    || value === 'down'
    || value === 'unknown'
  ) {
    return value
  }
  return 'unknown'
}

function findBffService(
  services: BffServiceHealth[],
  definition: BootServiceDefinition,
): BffServiceHealth | undefined {
  const aliases = new Set(definition.aliases.map(normalizeServiceName))
  return services.find((service) => aliases.has(normalizeServiceName(service.name)))
}

function mapBffService(
  definition: BootServiceDefinition,
  services: BffServiceHealth[],
): ServiceCheck {
  const service = findBffService(services, definition)
  if (!service) {
    return {
      ...serviceFromDefinition(definition, 'unknown'),
      error: 'Not reported by health BFF',
    }
  }

  const status = coerceBffStatus(service.status)
  const error = readString(service.error)
  return {
    ...serviceFromDefinition(definition, status),
    endpoint: readString(service.endpoint) ?? bffEndpointFor(definition),
    responseTimeMs: readNumber(service.response_time_ms) ?? readNumber(service.responseTimeMs),
    error: error ?? (status === 'unknown' ? 'BFF status unknown' : undefined),
  }
}

function mapBffFailure(message: string): ServiceCheck[] {
  return serviceDefinitions.map((definition) => ({
    ...serviceFromDefinition(definition, definition.aliases[0] === 'backend' ? 'down' : 'unknown'),
    error: definition.aliases[0] === 'backend' ? message : 'Health BFF unavailable',
  }))
}

function errorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') return 'Timeout (5s)'
  if (error instanceof Error) return error.message
  return 'Health BFF request failed'
}

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

  // Cockpit readiness is sourced from the server-side health BFF.
  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    const checkHealthBff = async () => {
      const start = performance.now()
      const timeoutId = setTimeout(() => controller.abort(), 5000)
      setProgress(15)

      try {
        const response = await fetch(HEALTH_BFF_ENDPOINT, {
          method: 'GET',
          signal: controller.signal,
          cache: 'no-store',
        })

        let parsedBody: unknown = null
        try {
          parsedBody = await response.json()
        } catch {
          parsedBody = null
        }

        if (cancelled) return

        const bffServices = readBffServices(parsedBody)
        if (bffServices.length > 0) {
          setServices(serviceDefinitions.map((definition) => mapBffService(definition, bffServices)))
        } else {
          const elapsed = Math.round(performance.now() - start)
          setServices(mapBffFailure(`Health BFF returned HTTP ${response.status}`).map((service) => (
            service.name === 'Backend API'
              ? { ...service, responseTimeMs: elapsed }
              : service
          )))
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const elapsed = Math.round(performance.now() - start)
          setServices(mapBffFailure(errorMessage(err)).map((service) => (
            service.name === 'Backend API'
              ? { ...service, responseTimeMs: elapsed }
              : service
          )))
        }
      } finally {
        clearTimeout(timeoutId)
        if (!cancelled) {
          setProgress(100)
          setIsBooting(false)
        }
      }
    }

    checkHealthBff()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [])

  const requiredHealthy = services.filter(s => s.required && s.status === 'healthy').length
  const requiredTotal = services.filter(s => s.required).length
  const allRequiredHealthy = requiredTotal > 0 && requiredHealthy === requiredTotal

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
                  {typeof service.responseTimeMs === 'number' && (
                    <span className="text-xs text-muted-foreground font-mono">
                      {service.responseTimeMs}ms
                    </span>
                  )}
                  {getStatusIcon(service.status)}
                </div>
              </div>
            ))}
          </div>

          {/* BFF notice */}
          {!isBooting && services.some(s => s.status === 'unknown') && (
            <p className="text-xs text-muted-foreground text-center">
              Some statuses are unknown because the health BFF did not verify them.
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
