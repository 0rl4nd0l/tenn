# Textual Output Contract

When an evidence envelope is available, `/sources list` renders:

```text
Sources list (evidence envelope; use `/sources show <n>` to inspect a specific source):
  taxonomy: <source_label_taxonomy_version>
  coverage_status: <source_coverage_status>
   1. <source_name> [<source_id>] (status=<status>; labels=<evidence_labels>; items=<item_count>; claim_verified=<true|false>; ...)
```

The list preserves exact envelope labels instead of converting them into generic "source-backed" wording.

Visible per-source states include:

- `claim_verified`
- `context_only`
- `no_hit`
- `operational_trace`
- `local_personal_data`
- `memory_context`
- `external_web_context`
- `local_news_context`
- `financial_truth`
- `degraded_runtime`
- `missing_required_evidence`
- `unknown_unclassified`

When an evidence envelope is available, `/sources show <n>` renders:

```text
Source <n>: <source_name>
  id: <source_id>
  taxonomy: <source_label_taxonomy_version>
  coverage_status: <source_coverage_status>
  status: <status>
  evidence_label: <evidence_label>
  evidence_labels: <evidence_labels>
  source_role_labels: <source_role_labels>
  item_count: <item_count>
  has_evidence: <true|false>
  claim_verified: <true|false>
  no_hit: <true|false>
  degraded: <true|false>
  missing_required_evidence: <true|false>
  missing_categories: <missing_categories>
  error: <error>
```

Safe fallback when no envelope exists:

```text
Evidence taxonomy: unavailable; legacy source payloads are listed for inspection only and are not verification labels.
```

Fallback behavior deliberately avoids generic verified/source-backed wording.
