import type { ProviderCapabilitySnapshot, RuntimeId } from "../../shared/types";

import type { AgentAdapter } from "./base";
import { ClaudeAdapter } from "./claude";
import { CodexCloudAdapter } from "./codex-cloud";
import { CodexLocalAdapter } from "./codex-local";
import { CursorAdapter } from "./cursor";
import { GenericAdapter } from "./generic";
import { GeminiAdapter } from "./gemini";
import { OpenCodeAdapter } from "./opencode";

export class AdapterRegistry {
  private readonly adapters: Map<RuntimeId, AgentAdapter>;

  constructor(adapters?: AgentAdapter[]) {
    const instances =
      adapters ??
      [
        new CodexLocalAdapter(),
        new CodexCloudAdapter(),
        new ClaudeAdapter(),
        new GeminiAdapter(),
        new CursorAdapter(),
        new OpenCodeAdapter(),
        new GenericAdapter()
      ];
    this.adapters = new Map(instances.map((adapter) => [adapter.runtime, adapter]));
  }

  get(runtime: RuntimeId): AgentAdapter {
    const adapter = this.adapters.get(runtime);
    if (!adapter) {
      throw new Error(`No adapter registered for ${runtime}`);
    }
    return adapter;
  }

  list(): AgentAdapter[] {
    return [...this.adapters.values()];
  }

  async detectAllCapabilities(): Promise<ProviderCapabilitySnapshot[]> {
    return Promise.all(this.list().map((adapter) => adapter.detectCapability()));
  }

  async detectCapability(runtime: RuntimeId): Promise<ProviderCapabilitySnapshot> {
    return this.get(runtime).detectCapability();
  }

  async spawn(runtime: RuntimeId, input: Parameters<AgentAdapter["spawn"]>[0]) {
    return this.get(runtime).spawn(input);
  }

  async followUp(runtime: RuntimeId, input: Parameters<AgentAdapter["followUp"]>[0]) {
    return this.get(runtime).followUp(input);
  }

  async cancel(runtime: RuntimeId, sessionId: string, externalId?: string | null) {
    return this.get(runtime).cancel(sessionId, externalId);
  }

  async isAlive(runtime: RuntimeId, sessionId: string, externalId?: string | null) {
    return this.get(runtime).isAlive(sessionId, externalId);
  }
}

export function createAdapterRegistry(): AdapterRegistry {
  return new AdapterRegistry();
}

export async function refreshCapabilities(registry: AdapterRegistry): Promise<ProviderCapabilitySnapshot[]> {
  return registry.detectAllCapabilities();
}
