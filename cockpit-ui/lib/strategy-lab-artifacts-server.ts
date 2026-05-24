import { readFileSync } from 'node:fs';
import path from 'node:path';

import {
  STRATEGY_LAB_REVIEW_SOURCES,
  buildStrategyLabArtifactsResponse,
  type StrategyLabArtifactsResponse,
  type StrategyLabReviewArtifact,
  type StrategyLabReviewSource,
} from './strategy-lab-artifacts';
import { resolveStrategyLabWorkspaceRoot } from './strategy-lab-status-server';

export interface ReadStrategyLabArtifactsOptions {
  now?: Date;
  workspaceRoot?: string;
}

export function readStrategyLabArtifacts(
  options: ReadStrategyLabArtifactsOptions = {},
): StrategyLabArtifactsResponse {
  const workspaceRoot = resolveStrategyLabWorkspaceRoot(options.workspaceRoot);
  const generatedAt = (options.now ?? new Date()).toISOString();
  const artifacts = STRATEGY_LAB_REVIEW_SOURCES.map((source) =>
    readReviewArtifactFromSource(source, workspaceRoot),
  );

  return buildStrategyLabArtifactsResponse({ generatedAt, artifacts });
}

function readReviewArtifactFromSource(
  source: StrategyLabReviewSource,
  workspaceRoot: string,
): StrategyLabReviewArtifact {
  const absolutePath = path.join(workspaceRoot, source.source_path);

  if (source.evidence_kind === 'report_evidence') {
    return readReportEvidence(source, absolutePath);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(absolutePath, 'utf-8')) as unknown;
  } catch (error) {
    return {
      ...baseArtifact(source),
      availability: isFileReadError(error) ? 'missing' : 'invalid_json',
      data_missing: uniqueStrings([...source.data_missing, 'parseable_json']),
    };
  }

  const record = isRecord(parsed) ? parsed : {};
  return {
    ...baseArtifact(source),
    availability: 'available',
    source_report_path: firstString([
      valueAt(record, ['provenance', 'source_report_path']),
      source.source_path,
    ]),
    schema_version: stringValue(record.schema_version),
    artifact_id: stringValue(record.artifact_id),
    artifact_type: stringValue(record.artifact_type),
    review_status: stringValue(record.review_status),
    result_status: stringValue(record.result_status),
    canonical_financial_truth: booleanOrMissing(record.canonical_financial_truth),
    execution_allowed: booleanOrMissing(record.execution_allowed),
    store_writes: deriveStoreWrites(record),
    data_missing: uniqueStrings([
      ...source.data_missing,
      ...stringArrayValue(record.data_missing),
      ...(source.authoritative ? [] : ['not_authoritative_strategy_lab_artifact_v1']),
    ]),
  };
}

function readReportEvidence(
  source: StrategyLabReviewSource,
  absolutePath: string,
): StrategyLabReviewArtifact {
  try {
    readFileSync(absolutePath, 'utf-8');
  } catch {
    return {
      ...baseArtifact(source),
      availability: 'missing',
      data_missing: uniqueStrings([...source.data_missing, 'report_file']),
    };
  }

  return {
    ...baseArtifact(source),
    availability: 'available',
    artifact_type: 'report',
    review_status: 'DATA_MISSING',
    result_status: 'REPORT_ONLY',
    schema_version: 'DATA_MISSING',
    source_report_path: source.source_path,
    data_missing: uniqueStrings([...source.data_missing, 'artifact_envelope']),
  };
}

function baseArtifact(source: StrategyLabReviewSource): StrategyLabReviewArtifact {
  return {
    id: source.id,
    label: source.label,
    evidence_kind: source.evidence_kind,
    authoritative: source.authoritative,
    availability: 'missing',
    source_path: source.source_path,
    source_report_path: 'DATA_MISSING',
    schema_version: 'DATA_MISSING',
    artifact_id: 'DATA_MISSING',
    artifact_type: 'DATA_MISSING',
    review_status: 'DATA_MISSING',
    result_status: 'DATA_MISSING',
    canonical_financial_truth: 'DATA_MISSING',
    execution_allowed: 'DATA_MISSING',
    store_writes: 'DATA_MISSING',
    what_it_proves: source.what_it_proves,
    what_it_does_not_prove: source.what_it_does_not_prove,
    data_missing: source.data_missing,
  };
}

function deriveStoreWrites(record: Record<string, unknown>): boolean | 'DATA_MISSING' {
  const fields = [
    record.may_write_db,
    record.may_write_qdrant,
    record.may_write_memory,
    record.may_write_financial_truth,
    valueAt(record, ['storage_policy', 'may_write_db']),
    valueAt(record, ['storage_policy', 'may_write_qdrant']),
    valueAt(record, ['storage_policy', 'may_write_memory']),
    valueAt(record, ['storage_policy', 'may_write_financial_truth']),
  ];

  const booleans = fields.filter((value): value is boolean => typeof value === 'boolean');
  if (booleans.length === 0) {
    return 'DATA_MISSING';
  }

  return booleans.some(Boolean);
}

function isFileReadError(error: unknown): boolean {
  return isRecord(error) && error.code === 'ENOENT';
}

function booleanOrMissing(value: unknown): boolean | 'DATA_MISSING' {
  return typeof value === 'boolean' ? value : 'DATA_MISSING';
}

function stringValue(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value : 'DATA_MISSING';
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : [];
}

function firstString(values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }
  return 'DATA_MISSING';
}

function valueAt(record: Record<string, unknown>, pathParts: string[]): unknown {
  let current: unknown = record;
  for (const part of pathParts) {
    if (!isRecord(current)) {
      return undefined;
    }
    current = current[part];
  }
  return current;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.trim().length > 0)));
}
