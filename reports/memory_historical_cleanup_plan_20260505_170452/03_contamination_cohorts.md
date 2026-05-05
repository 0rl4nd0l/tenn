# Contamination Cohorts

## Cohort Findings

- Pettimed capital raising fanout: present as the largest copied-DB duplicate cluster and corroborated by stocktake. Matching Pettimed/PET/PETT rows are preserved or alias-reviewed; unrelated copies are status-expire candidates when the statement target is explicit.
- Largest transcript cluster: source `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` fans out across many unrelated company scopes. The copied DB cluster rollup is in `csv/fanout_cluster_cleanup_candidates.csv`.
- Atlassian result / tech-strength cluster: Atlassian-specific rows are preserved under ATLASSIAN; tech-strength and Asian-stocks rows are market rehome candidates or manual review, not company-specific BHP/A2M/ACC evidence.
- A2M recall entries: A2M/A2 MILK recall rows are preserved or alias-merge-later candidates; copies under unrelated company scopes are expire candidates when explicit A2M text is present.
- BHP contaminated scope: true BHP rows such as BHP/Big Australian/copper-potash statements are preserved. Atlassian, A2M, Pettimed, Accent, macro, and raw portfolio rows under BHP are expire, rehome, or manual-review candidates by row id.
- Healthcare batch fanout: 4DMEDICAL, AROVELLA, CSL, RESMED, EZZ, LTR PHARMA, and Paradigm rows are split by explicit target matching. Raw dict-like healthcare recap rows are manual review first; non-raw explicit mismatches become expire candidates.
- Alias-fragmented groups: A2M/A2 MILK, ACC/ACCENT GROUP, PET/PETT/PETTIMED, GCM/GCMC/GCM CORPORATION, MAR/MARINO/MARINO AND CO, KEY/KEYP/KEY PETROLEUM, WIN/WIN MEDALS, and END/EDV/ENDV/ENDEAVOR GROUP remain alias-merge-later only. No live alias canonicalization is proposed.
- Raw dict-like rows: classified as `candidate_raw_payload_review` and routed to manual review. This plan does not auto-expire raw rows solely because they are raw.
- Macro/education/strategy rows: classified as market or macro wrong-store candidates when source/provenance is sufficient for a future rehome review; otherwise manual review or blocked.

## Primary Evidence Files

- `reports/full_system_stocktake_20260505_152038/04A_memory_scope_classification.csv`
- `reports/full_system_stocktake_20260505_152038/04A_memory_duplicate_fanout_clusters.csv`
- `reports/full_system_stocktake_20260505_152038/04A_memory_alias_fragmentation_matrix.csv`
- `reports/full_system_stocktake_20260505_152038/04A_memory_provenance_gaps.csv`
- `reports/full_system_stocktake_20260505_152038/04A_memory_write_path_trace.md`
- `reports/full_system_stocktake_20260505_152038/04A_memory_retrieval_risk_report.md`
- `reports/memory_contamination_root_cause_20260505_161634`
- `reports/memory_signal_router_fanout_guard_20260505_164348`
