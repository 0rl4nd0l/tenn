'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Cpu, Server, ToggleLeft, Info, GitBranch, FolderOpen, Loader2, HardDrive } from 'lucide-react'
import { useCockpitStore } from '@/lib/cockpit-store'
import { fetchAvailableModels } from '@/lib/api-client'
import type { ModelGroup } from '@/lib/cockpit-types'

interface ConfigSectionProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
}

function ConfigSection({ title, icon, children }: ConfigSectionProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {children}
      </CardContent>
    </Card>
  )
}

interface ConfigRowProps {
  label: string
  value: string | number | boolean
  mono?: boolean
}

function ConfigRow({ label, value, mono = false }: ConfigRowProps) {
  const displayValue = typeof value === 'boolean' ? (value ? 'Enabled' : 'Disabled') : String(value)

  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      {typeof value === 'boolean' ? (
        <Badge variant={value ? 'default' : 'secondary'} className="text-xs">
          {displayValue}
        </Badge>
      ) : (
        <span className={`text-sm ${mono ? 'font-mono' : ''}`}>{displayValue}</span>
      )}
    </div>
  )
}

interface ConfigState {
  llm: {
    model: string
    endpoint: string
    routingPolicy: string
    apiKeyConfigured: boolean
    maxTokens: number
    temperature: number
  }
  backend: {
    url: string
    profile: string
  }
  features: {
    webSearch: boolean
    rag: boolean
    extraction: boolean
  }
  environment: {
    pythonVersion: string
    gitBranch: string
    dataRoot: string
  }
}

const DEFAULTS: ConfigState = {
  llm: {
    model: 'model:qwen3.5-35b-a3b',
    endpoint: 'http://localhost:8001',
    routingPolicy: 'local-first',
    apiKeyConfigured: false,
    maxTokens: 4096,
    temperature: 0.7,
  },
  backend: {
    url: 'http://localhost:8000',
    profile: 'unknown',
  },
  features: {
    webSearch: true,
    rag: true,
    extraction: true,
  },
  environment: {
    pythonVersion: 'unknown',
    gitBranch: 'unknown',
    dataRoot: '/data/financial-engine',
  },
}

export function SettingsScreen() {
  const { chatModel, setChatModel, preferences } = useCockpitStore()
  const [config, setConfig] = useState<ConfigState>(DEFAULTS)
  const [modelGroups, setModelGroups] = useState<ModelGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [backendOnline, setBackendOnline] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchConfig() {
      setLoading(true)
      setError(null)

      let healthOk = false

      // 1. Check backend health (no auth)
      try {
        const healthRes = await fetch('/api/health')
        if (healthRes.ok) {
          healthOk = true
          setBackendOnline(true)
        }
      } catch {
        // backend unreachable
      }

      // 2. Fetch cockpit config (no API key required)
      try {
        const statusRes = await fetch('/api/cockpit/config')

        if (statusRes.ok) {
          const status = await statusRes.json()

          setConfig((prev) => ({
            llm: {
              model: status.llm_model || status.model || prev.llm.model,
              endpoint: status.llm_endpoint || prev.llm.endpoint,
              routingPolicy: status.routing_policy || prev.llm.routingPolicy,
              apiKeyConfigured:
                typeof status.anthropic_key_configured === 'boolean'
                  ? status.anthropic_key_configured
                  : prev.llm.apiKeyConfigured,
              maxTokens: status.max_tokens || prev.llm.maxTokens,
              temperature: status.temperature ?? prev.llm.temperature,
            },
            backend: {
              url: status.backend_url || prev.backend.url,
              profile: status.profile || prev.backend.profile,
            },
            features: {
              webSearch: prev.features.webSearch,
              rag: prev.features.rag,
              extraction: status.features?.extraction ?? prev.features.extraction,
            },
            environment: {
              pythonVersion: status.python_version || prev.environment.pythonVersion,
              gitBranch: status.git_branch || prev.environment.gitBranch,
              dataRoot: status.data_root || prev.environment.dataRoot,
            },
          }))
        } else {
          if (!healthOk) {
            setError('Backend unreachable and system status unavailable')
          }
        }
      } catch {
        if (!healthOk) {
          setError('Failed to connect to backend')
        }
      }

      // 3. Fetch available models
      try {
        const modelsData = await fetchAvailableModels()
        setModelGroups(modelsData.groups)
      } catch {
        // Non-fatal — model list just won't be dynamic
      }

      setLoading(false)
    }

    fetchConfig()
  }, [])

  useEffect(() => {
    setConfig((prev) => ({
      ...prev,
      features: {
        ...prev.features,
        webSearch: preferences.webSearchEnabled,
        rag: preferences.ragEnabled,
      },
    }))
  }, [preferences.ragEnabled, preferences.webSearchEnabled])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading configuration...</span>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold">Configuration</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Read-only view of cockpit configuration and capabilities
          </p>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant={backendOnline ? 'default' : 'critical'} className="text-xs font-mono">
              {backendOnline ? 'BACKEND RUNNING' : 'BACKEND DOWN'}
            </Badge>
            {error && (
              <Badge variant="critical" className="text-xs font-mono">CRITICAL: {error}</Badge>
            )}
          </div>
        </div>

        {/* LLM Configuration */}
        <ConfigSection title="LLM Configuration" icon={<Cpu className="h-5 w-5 text-primary" />}>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-muted-foreground">Chat Model</span>
            <Select value={chatModel} onValueChange={setChatModel}>
              <SelectTrigger className="w-[340px] h-8 text-sm font-mono">
                <SelectValue placeholder="Select a model..." />
              </SelectTrigger>
              <SelectContent>
                {modelGroups.length > 0 ? (
                  modelGroups.map((group) => (
                    <div key={group.location}>
                      <div className="flex items-center gap-1.5 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        <HardDrive className="h-3 w-3" />
                        {group.label}
                      </div>
                      {group.models.map((m) => (
                        <SelectItem
                          key={`${group.location}:${m.id}`}
                          value={m.id}
                          disabled={!m.available}
                        >
                          <div className="flex items-center justify-between w-full gap-3">
                            <span className="font-mono text-sm truncate">{m.id}</span>
                            <span className="text-xs text-muted-foreground shrink-0">
                              {m.size_gb > 0 ? `${m.size_gb}G` : ''}{m.quantization ? `${m.size_gb > 0 ? ' ' : ''}${m.quantization}` : ''}
                              {!m.available ? ' (cold)' : ''}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </div>
                  ))
                ) : (
                  <SelectItem value={chatModel}>
                    <span className="font-mono text-sm">{chatModel}</span>
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
          <Separator />
          <ConfigRow label="Endpoint" value={config.llm.endpoint} mono />
          <Separator />
          <ConfigRow label="Routing Policy" value={config.llm.routingPolicy} mono />
          <Separator />
          <ConfigRow label="Anthropic API Key" value={config.llm.apiKeyConfigured} />
          <Separator />
          <ConfigRow label="Max Tokens" value={config.llm.maxTokens} mono />
          <Separator />
          <ConfigRow label="Temperature" value={config.llm.temperature} mono />
        </ConfigSection>

        {/* Backend Configuration */}
        <ConfigSection title="Backend Configuration" icon={<Server className="h-5 w-5 text-primary" />}>
          <ConfigRow label="URL" value={config.backend.url} mono />
          <Separator />
          <ConfigRow label="Profile" value={config.backend.profile} />
        </ConfigSection>

        {/* Feature Flags */}
        <ConfigSection title="Feature Flags" icon={<ToggleLeft className="h-5 w-5 text-primary" />}>
          <ConfigRow label="Web Search" value={config.features.webSearch} />
          <Separator />
          <ConfigRow label="RAG" value={config.features.rag} />
          <Separator />
          <ConfigRow label="Extraction" value={config.features.extraction} />
          <p className="text-xs text-muted-foreground">
            Web Search and RAG reflect the current cockpit session toggles from Operations. Extraction reflects backend runtime capability.
          </p>
        </ConfigSection>

        {/* Environment */}
        <ConfigSection title="Environment" icon={<Info className="h-5 w-5 text-primary" />}>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-muted-foreground">Python Version</span>
            <Badge variant="outline" className="text-xs font-mono">
              {config.environment.pythonVersion}
            </Badge>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-muted-foreground flex items-center gap-2">
              <GitBranch className="h-3 w-3" />
              Git Branch
            </span>
            <Badge variant="outline" className="text-xs font-mono">
              {config.environment.gitBranch}
            </Badge>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-muted-foreground flex items-center gap-2">
              <FolderOpen className="h-3 w-3" />
              Data Root
            </span>
            <span className="text-sm font-mono text-muted-foreground truncate max-w-[300px]">
              {config.environment.dataRoot}
            </span>
          </div>
        </ConfigSection>

        {/* Capabilities */}
        <ConfigSection title="Capabilities" icon={<Info className="h-5 w-5 text-primary" />}>
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">Financial Analysis</Badge>
            <Badge variant="default">Document Processing</Badge>
            <Badge variant="default">Metric Extraction</Badge>
            <Badge variant="default">News Ingestion</Badge>
            <Badge variant="default">Chart Generation</Badge>
            <Badge variant="secondary">Vector Search</Badge>
            <Badge variant="secondary">Web Scraping</Badge>
            <Badge variant="outline">Deep Research</Badge>
          </div>
        </ConfigSection>
      </div>
    </ScrollArea>
  )
}
