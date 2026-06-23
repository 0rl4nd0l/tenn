# Design

## Problem

PR #385 added `check-closeout`, but the exemption detector treated any
occurrence of `control-plane`, `docs-only`, or `report-only` as a non-runtime
scope declaration. That could exempt a runtime-like task card merely because
its text mentioned control-plane status work or said "not report-only".

## Change

- Runtime-like detection still scans the task card metadata/body for daemon,
  runtime, extraction, automation, product, data, service, scheduler, collector,
  ingestion, and pipeline terms.
- Non-runtime exemption now requires explicit declaration through:
  - frontmatter `closeout_scope: report_only`;
  - frontmatter `closeout_scope: docs_only`;
  - frontmatter `closeout_scope: control_plane_only`;
  - equivalent `Closeout scope: ...`, `Task scope: ...`, `Mode: ...`, or
    `This task is ...` body lines.
- Casual mentions of `control-plane`, `report-only`, or `docs-only` do not
  exempt a runtime-like card.

## Scope Boundary

This is control-plane validation tooling only. It does not touch Tenn runtime,
product data, extraction logic, count-24, greyhound runtime, or host-global
files.
