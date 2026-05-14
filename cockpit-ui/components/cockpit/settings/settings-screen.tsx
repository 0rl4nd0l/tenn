'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Cpu, Server, ToggleLeft, Info, GitBranch, FolderOpen, Loader2, HardDrive, ArrowRightLeft, Store, FileCode2 } from 'lucide-react'
import { useCockpitStore } from '@/lib/cockpit-store'
import { fetchAvailableModels, loadCockpitModel } from '@/lib/api-client'
import type { ChatRuntimeTarget, ModelGroup } from '@/lib/cockpit-types'
import { cn } from '@/lib/utils'
import { PromptLabPanel } from './prompt-lab-panel'

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
    runtimeTarget: ChatRuntimeTarget
    rentedGpuConfigured: boolean
    rentedGpuHealthy: boolean
    rentedGpuEndpoint: string
    rentedGpuError: string
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
    model: 'model:qwen3.5-35b-a3b-apex',
    endpoint: 'http://localhost:8001',
    routingPolicy: 'local-first',
    runtimeTarget: 'local',
    rentedGpuConfigured: false,
    rentedGpuHealthy: false,
    rentedGpuEndpoint: '',
    rentedGpuError: '',
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

const ROUTING_POLICY_OPTIONS = [
  { value: 'config_default', label: 'Config default' },
  { value: 'local_preferred', label: 'Local preferred' },
  { value: 'local_only', label: 'Local only' },
  { value: 'api_preferred', label: 'API preferred' },
  { value: 'api_only', label: 'API only' },
] as const

const RUNTIME_TARGET_OPTIONS: Array<{ value: ChatRuntimeTarget; label: string; description: string }> = [
  { value: 'local', label: 'Local', description: 'Use this workstation runtime.' },
  { value: 'rented_gpu', label: 'Rented GPU', description: 'Use the configured remote llama.cpp endpoint.' },
  { value: 'auto', label: 'Auto', description: 'Use rented GPU for heavier strategy/context turns when configured.' },
]

export function SettingsScreen() {
  const { chatModel, setChatModel, preferences, updatePreferences } = useCockpitStore()
  const [config, setConfig] = useState<ConfigState>(DEFAULTS)
  const [modelGroups, setModelGroups] = useState<ModelGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [backendOnline, setBackendOnline] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [switching, setSwitching] = useState(false)
  const [switchResult, setSwitchResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'runtime' | 'prompt-lab'>('runtime')

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
              runtimeTarget: (status.runtime_target || prev.llm.runtimeTarget) as ChatRuntimeTarget,
              rentedGpuConfigured:
                typeof status.rented_gpu?.configured === 'boolean'
                  ? status.rented_gpu.configured
                  : prev.llm.rentedGpuConfigured,
              rentedGpuHealthy:
                typeof status.rented_gpu?.healthy === 'boolean'
                  ? status.rented_gpu.healthy
                  : prev.llm.rentedGpuHealthy,
              rentedGpuEndpoint: status.rented_gpu?.endpoint || prev.llm.rentedGpuEndpoint,
              rentedGpuError: status.rented_gpu?.error || '',
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
              webSearch:
                typeof status.features?.web_search === 'boolean'
                  ? status.features.web_search
                  : prev.features.webSearch,
              rag:
                typeof status.features?.rag === 'boolean'
                  ? status.features.rag
                  : prev.features.rag,
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

  const isIPhoneScale = preferences.iphoneScale

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
      <div className={cn(
        "mx-auto transition-all duration-300",
        activeTab === 'prompt-lab' ? "max-w-7xl" : "max-w-4xl",
        isIPhoneScale ? "p-3 space-y-3" : "p-6 space-y-6"
      )}>
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold">Configuration</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Cockpit configuration, runtime capabilities, and saved UI preferences
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Settings are limited in this build; core runtime and Marketplace defaults are available below.
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

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)}>
          <TabsList>
            <TabsTrigger value="runtime">
              <Cpu className="h-4 w-4" />
              Runtime
            </TabsTrigger>
            <TabsTrigger value="prompt-lab">
              <FileCode2 className="h-4 w-4" />
              Prompt Lab
            </TabsTrigger>
          </TabsList>

          <TabsContent value="runtime" className="space-y-6">
        {/* LLM Configuration */}
        <ConfigSection title="LLM Configuration" icon={<Cpu className="h-5 w-5 text-primary" />}>
          <div className={cn(
            "flex items-center justify-between py-2 gap-4",
            isIPhoneScale && "flex-col items-start"
          )}>
            <span className="text-sm text-muted-foreground">Chat Model</span>
            <div className={cn(
              "flex items-center gap-2",
              isIPhoneScale && "w-full"
            )}>
              <Select value={chatModel} onValueChange={(value) => {
                setChatModel(value)
                const selectedRuntime = modelGroups
                  .flatMap((group) => group.models.map((model) => (
                    model.id === value ? (model.runtime_target || group.runtime_target) : null
                  )))
                  .find(Boolean)
                if (selectedRuntime === 'rented_gpu') {
                  updatePreferences({ chatRuntimeTarget: 'rented_gpu' })
                }
                setSwitchResult(null)
              }}>
                <SelectTrigger className={cn(
                  "h-8 text-sm font-mono",
                  isIPhoneScale ? "flex-1" : "w-[300px]"
                )}>
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
              <Button
                variant="default"
                size="sm"
                className="h-8 gap-1.5 shrink-0"
                disabled={switching || !backendOnline}
                onClick={async () => {
                  setSwitching(true)
                  setSwitchResult(null)
                  try {
                    const result = await loadCockpitModel(chatModel, preferences.chatRuntimeTarget)
                    setSwitchResult({ ok: result.ok, message: result.message })
                  } catch (err: unknown) {
                    setSwitchResult({
                      ok: false,
                      message: err instanceof Error ? err.message : 'Switch failed',
                    })
                  } finally {
                    setSwitching(false)
                  }
                }}
              >
                {switching ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ArrowRightLeft className="h-3.5 w-3.5" />
                )}
                Switch
              </Button>
            </div>
          </div>
          {switchResult && (
            <div className={`text-xs px-3 py-1.5 rounded ${
              switchResult.ok
                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                : 'bg-destructive/10 text-destructive border border-destructive/20'
            }`}>
              {switchResult.message}
            </div>
          )}
          <Separator />
          <ConfigRow label="Endpoint" value={config.llm.endpoint} mono />
          <Separator />
          <ConfigRow
            label="Chat Runtime Target"
            value={preferences.chatRuntimeTarget}
            mono
          />
          <Separator />
          <div className={cn(
            "flex items-start justify-between py-2 gap-4",
            isIPhoneScale && "flex-col items-start"
          )}>
            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">Runtime Toggle</span>
              <p className="text-xs text-muted-foreground">
                Select local for default operation, rented GPU for advanced remote runs, or auto for heavier strategy/context turns.
              </p>
            </div>
            <Select
              value={preferences.chatRuntimeTarget}
              onValueChange={(value) => {
                updatePreferences({
                  chatRuntimeTarget: value as ChatRuntimeTarget,
                })
                setSwitchResult(null)
              }}
            >
              <SelectTrigger className={cn(
                "h-8 text-sm font-mono",
                isIPhoneScale ? "w-full" : "w-[220px]"
              )}
              aria-label="Chat runtime target">
                <SelectValue placeholder="Local" />
              </SelectTrigger>
              <SelectContent>
                {RUNTIME_TARGET_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="text-xs text-muted-foreground">
            {RUNTIME_TARGET_OPTIONS.find((option) => option.value === preferences.chatRuntimeTarget)?.description}
          </div>
          <Separator />
          <ConfigRow
            label="Rented GPU Endpoint"
            value={config.llm.rentedGpuEndpoint || 'not configured'}
            mono
          />
          <Separator />
          <ConfigRow
            label="Rented GPU Health"
            value={
              config.llm.rentedGpuHealthy
                ? 'healthy'
                : config.llm.rentedGpuConfigured
                  ? `unhealthy${config.llm.rentedGpuError ? `: ${config.llm.rentedGpuError}` : ''}`
                  : 'not configured'
            }
            mono
          />
          <Separator />
          <ConfigRow label="Effective Routing Policy" value={config.llm.routingPolicy} mono />
          <Separator />
          <div className={cn(
            "flex items-center justify-between py-2 gap-4",
            isIPhoneScale && "flex-col items-start"
          )}>
            <span className="text-sm text-muted-foreground">Chat Route Override</span>
            <Select
              value={preferences.chatRoutingPolicyOverride}
              onValueChange={(value) => {
                updatePreferences({
                  chatRoutingPolicyOverride: value as typeof preferences.chatRoutingPolicyOverride,
                })
              }}
            >
              <SelectTrigger className={cn(
                "h-8 text-sm font-mono",
                isIPhoneScale ? "w-full" : "w-[220px]"
              )}
              aria-label="Chat route override">
                <SelectValue placeholder="Config default" />
              </SelectTrigger>
              <SelectContent>
                {ROUTING_POLICY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
          <ConfigRow label="Runtime Profile" value={config.backend.profile} />
        </ConfigSection>

        {/* Feature Flags */}
        <ConfigSection title="Feature Flags" icon={<ToggleLeft className="h-5 w-5 text-primary" />}>
          <ConfigRow label="Web Search" value={config.features.webSearch} />
          <Separator />
          <ConfigRow label="RAG" value={config.features.rag} />
          <Separator />
          <ConfigRow label="Extraction" value={config.features.extraction} />
          <p className="text-xs text-muted-foreground">
            These flags reflect backend-authoritative defaults and runtime capability for new chat turns. Session-level overrides can still change an individual tab.
          </p>
        </ConfigSection>

        <ConfigSection title="Marketplace Preferences" icon={<Store className="h-5 w-5 text-primary" />}>
          <div className="space-y-2">
            <label htmlFor="marketplace-home-location" className="text-sm text-muted-foreground">
              Home location / suburb
            </label>
            <Input
              id="marketplace-home-location"
              value={preferences.marketplaceHomeLocation}
              placeholder="e.g. Melbourne, eastern suburbs"
              onChange={(event) => {
                updatePreferences({
                  marketplaceHomeLocation: event.target.value,
                })
              }}
            />
            <p className="text-xs text-muted-foreground">
              Used as the default location context for Marketplace assistant mission drafting.
            </p>
          </div>
          <Separator />
          <div className="flex items-start justify-between gap-4 py-1">
            <div className="space-y-1">
              <label htmlFor="marketplace-prefer-cloud-routing" className="text-sm text-muted-foreground">
                Prefer cloud routing for Marketplace assistant
              </label>
              <p className="text-xs text-muted-foreground">
                Forces Marketplace assistant chat turns onto the cloud/API route. Extraction-triggered API pinning still overrides this automatically.
              </p>
            </div>
            <Switch
              id="marketplace-prefer-cloud-routing"
              checked={preferences.marketplacePreferCloudRouting}
              onCheckedChange={(checked) => {
                updatePreferences({
                  marketplacePreferCloudRouting: checked,
                })
              }}
            />
          </div>
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
            <span className={cn(
              "text-sm font-mono text-muted-foreground truncate",
              isIPhoneScale ? "max-w-[150px]" : "max-w-[300px]"
            )}>
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
          </TabsContent>

          <TabsContent value="prompt-lab">
            {activeTab === 'prompt-lab' ? <PromptLabPanel /> : null}
          </TabsContent>
        </Tabs>
      </div>
    </ScrollArea>
  )
}
