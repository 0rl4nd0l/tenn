import { existsSync } from 'node:fs';
import path from 'node:path';

import {
  STRATEGY_LAB_BASELINE_REFS,
  buildStrategyLabStatusResponse,
  type StrategyLabArtifactRef,
  type StrategyLabStatusResponse,
} from './strategy-lab-status';

export interface ReadStrategyLabStatusOptions {
  now?: Date;
  workspaceRoot?: string;
}

export function resolveStrategyLabWorkspaceRoot(explicitRoot?: string): string {
  if (explicitRoot?.trim()) {
    return path.resolve(explicitRoot);
  }

  if (process.env.COCKPIT_WORKSPACE_ROOT?.trim()) {
    return path.resolve(process.env.COCKPIT_WORKSPACE_ROOT);
  }

  const cwd = process.cwd();
  return path.basename(cwd) === 'cockpit-ui' ? path.resolve(cwd, '..') : cwd;
}

export function readStrategyLabStatus(
  options: ReadStrategyLabStatusOptions = {},
): StrategyLabStatusResponse {
  const workspaceRoot = resolveStrategyLabWorkspaceRoot(options.workspaceRoot);
  const generatedAt = (options.now ?? new Date()).toISOString();
  const artifactRefs: StrategyLabArtifactRef[] = STRATEGY_LAB_BASELINE_REFS.map((ref) => ({
    ...ref,
    availability: existsSync(path.join(workspaceRoot, ref.path)) ? 'available' : 'missing',
  }));

  return buildStrategyLabStatusResponse({ generatedAt, artifactRefs });
}
