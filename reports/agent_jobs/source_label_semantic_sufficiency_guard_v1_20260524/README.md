# Source Label Semantic Sufficiency Guard

Implemented a deterministic semantic-sufficiency guard for source labels.

Confirmed behavior:
- Raw `claim_verified=true` / `supports_claim=true` is treated as context unless a deterministic label path already established `claim_verified`.
- Recent-news/recent-update claims require news, filing, announcement, or event evidence; price-only evidence is insufficient.
- Financial truth numeric context remains usable for canonical numbers but is not presented as event/news/narrative verification.
- Existing explicit claim-verified cases remain valid.

Review note: the first pass matched bare `today`/`yesterday`; that was narrowed and covered by regression test so ordinary price-status answers do not require news evidence.
