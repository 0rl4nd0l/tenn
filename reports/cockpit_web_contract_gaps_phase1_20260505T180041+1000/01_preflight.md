# Preflight

Required command results:
- `pwd`: `/home/l4nd0/tenn`
- `git branch --show-current`: `preserve/dirty-work-20260430T065748Z`
- Initial `git rev-parse HEAD`: `165be97d7e45632abd42fdebd2ef9b27805332d8`
- Current `git rev-parse HEAD` after live-branch drift: `c907cb8e0defdea3f429db56aac432b66e46e8d6`
- Current recent log head:
  - `c907cb8 milestone(reporting): add confirmed metric coverage verification UI`
  - `4ce73bd milestone(agent-jobs): add task card validator and watchdog helper`
  - `75fa09d milestone(memory): expire approved historical cleanup first batch`
  - `165be97 milestone(news): add safe qdrant projection repair mode`
  - `9721e1f audit(memory): dry-run historical expiry candidates`

Worktree:
- Primary worktree: `/mnt/sdb2/home/l4nd0/tenn` on `preserve/dirty-work-20260430T065748Z`
- Shell `pwd` resolves as `/home/l4nd0/tenn`; `git worktree list` shows the same worktree at `/mnt/sdb2/home/l4nd0/tenn`.
- Additional worktrees exist for baseline, repair, marketplace, holdings, and cloud audit branches.

Ancestor checks at current HEAD:
- `165be97d7e45632abd42fdebd2ef9b27805332d8`: ancestor yes
- `fb880c6ec0e2451855e80fbd203b924f14270ebc`: ancestor yes
- `22356f2139aa`: ancestor yes
- `a48c2e1a6389`: ancestor yes
- `d146f91`: ancestor yes
- `545181b`: ancestor yes
- `8860fe7`: ancestor yes
- `18712c6`: ancestor yes
- `82bfccb`: ancestor yes

Current dirty-file classification:
- Reporting: `cockpit-ui/components/cockpit/chat/chat-screen.tsx`, `cockpit-ui/components/cockpit/chat/terminal-message.tsx`, `cockpit-ui/lib/cockpit-types.ts`, gated `cockpit-ui/app/api/cockpit/commentary/ephemeral-index/*`, this report directory, and unrelated `cockpit-ui/next-env.d.ts`.
- Query Orchestration: `financial-engine_v2/cockpit/tests/test_chat_attached_sources.py`; unrelated dirty contested surface `financial-engine_v2/backend/app/routes/cockpit_api.py` was inspected read-only only.
- Marketplace: unrelated dirty `cockpit-ui/components/cockpit/marketplace/matches-screen*`, `cockpit-ui/lib/marketplace-api.ts`, `financial-engine_v2/backend/app/services/marketplace_*`, and related marketplace tests.
- Memory: no current dirty memory files. Initial preflight saw memory cleanup report artifacts, but live branch drift later moved HEAD to commits that include memory/reporting work.
- Extraction: no current dirty extraction files. Initial preflight saw confirmed metric coverage files; live branch drift later moved HEAD to a reporting commit that appears to include that work.
- News/Qdrant: none touched.
- unknown: `tenn_prompt_contracts_response_guidelines.zip`.

Collision decision:
- Proceeded because intended files were clean before editing and did not overlap with unrelated dirty files.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` is a contested surface and was not edited.
- Commit safety depends on staging only Phase 1 files and this report, not unrelated dirty files.
