# docs/research — Investigation and Decision Records

This directory contains read-only research artifacts: evaluations of external tools, ADR-style decision records, and deferred capability assessments.

These docs do NOT authorize implementation. They record what was investigated, what was decided, and what prerequisites must be met before a capability can be considered again.

---

## Index

| Doc | Decision | Status |
|-----|----------|--------|
| [autoresearch_evaluation.md](autoresearch_evaluation.md) | Do not adopt karpathy/autoresearch or pi-autoresearch directly; borrow patterns only; build Tenn-native dev optimization loop later when eval prerequisites are met | Deferred |
| [tenn_external_resource_viability_investigation.md](tenn_external_resource_viability_investigation.md) | Extend Tenn’s eval and audit layer; prefer DuckDB, Polars, MLflow, selective sklearn baselines, and tightly constrained Chandra or DSPy investigation; reject runtime-platform replacements | Complete |
| [tenn_external_resource_implementation_planning.md](tenn_external_resource_implementation_planning.md) | Sequence Tenn-safe adoption around measurement first: MLflow and DuckDB now, Chandra and DSPy after real-gold extraction eval, FMP and sklearn only after signal audit, and keep UI/runtime-heavy resources as pattern sources only | Complete |
