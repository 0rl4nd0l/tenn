
# Issue #96 Runtime Coverage Refresh

Generated: 2026-06-23T07:54:28.496693Z

Scope: approved confirmed metric fixture set (`financial-engine_v2/backend/tests/eval_fixtures`).

Result:
- Raw docs: 15
- Source PDFs resolved: 15
- Current terminal extraction payloads for fixture document IDs: 0
- Accepted payloads for fixture document IDs: 0

Interpretation: this is a report-local, no-DB refresh. It proves source PDFs are present, but it does not prove current runtime extraction coverage. All fixture documents remain `file_exists_no_current_terminal_run` until an approved bounded extraction pass supplies current terminal payloads.
