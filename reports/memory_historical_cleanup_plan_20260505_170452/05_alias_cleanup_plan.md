# Alias Cleanup Plan

Alias cleanup is deferred.

The candidate CSV `memory_rows_alias_merge_candidates.csv` marks rows where the row appears company-specific but lives under an alias-fragmented group. These rows must not be rewritten in live storage in the first cleanup pass.

Required later steps:

1. Build an authoritative ASX identity map outside the live memory DB.
2. Review each alias group with source titles, row ids, and original statements.
3. Decide whether canonicalization should be expire-and-reinsert, alias lookup at retrieval time, or a separate alias mapping table.
4. Preserve old row ids and original `company_id` values in an audit manifest before any mutation.
5. Run a copied-DB dry run before a live prompt.

Blocked alias groups for now: A2M/A2 MILK, ACC/ACCENT GROUP, PET/PETT/PETTIMED, GCM/GCMC/GCM CORPORATION, MAR/MARINO/MARINO AND CO, KEY/KEYP/KEY PETROLEUM, WIN/WIN MEDALS, and END/EDV/ENDV/ENDEAVOR GROUP.
