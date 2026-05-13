# Mutating Route Gate List

No mutating route was probed in this pass.

| route/control | owning surface | why mutating | future validation gate required | operator approval needed? |
| --- | --- | --- | --- | --- |
| `POST /api/cockpit/chat` | Chat | sends prompt, may invoke model/tools/session writes | Query Orchestration provenance smoke plan | yes |
| `POST /chat`, `POST /api/chat` | Legacy Chat | legacy chat execution path | legacy compatibility plan | yes |
| `POST /api/cockpit/chat/sessions` | Chat | creates/touches session | session fixture or disposable session approval | yes |
| `DELETE /api/cockpit/chat/sessions/{session_id}` | Chat | deletes session | disposable session only | yes |
| `POST /api/cockpit/chat/attachments/upload` | Chat | uploads attachment metadata/blob | fixture upload plan | yes |
| `POST /api/cockpit/claims/verify` | Chat/Verification | runs verification over assistant text/context | mocked or fixture request plan | yes |
| `POST /api/cockpit/feedback` | Chat feedback | writes feedback artifact | feedback artifact task card | yes |
| `POST /api/cockpit/feedback/flag` | Issue capture | creates flagged report | flagged-report task card | yes |
| `POST /api/cockpit/feedback/flags/{reportId}/deploy` | Feedback deploy | can spawn local deploy/fix process | explicit flagged-fix closeout protocol | yes |
| `GET /api/cockpit/feedback/flags/{reportId}/investigation` / local alias | Feedback investigation | may spawn or inspect local investigation workflow depending handler | explicit operator gate | yes |
| `POST /api/cockpit/action/preview` | Operations | preview may evaluate action inputs and command plans | action-specific dry-run task | yes |
| `POST /api/cockpit/action/execute` | Operations/Marketplace | executes action or starts background job | action task card and operator approval | yes |
| `POST /api/cockpit/action/jobs/{jobId}/stop` | Operations/Marketplace | stops active job | known disposable job only | yes |
| `POST /api/cockpit/restart` | Operations/Settings | restarts backend process | maintenance window task | yes |
| `POST /api/cockpit/models/load` | Settings/Boot | loads/reloads model, changes runtime/VRAM | GPU guard and operator approval | yes |
| `POST /api/cockpit/watchlist` | Watchlist | creates watchlist item | disposable local fixture | yes |
| `DELETE /api/cockpit/watchlist/{ticker}` | Watchlist | deletes watchlist item | disposable local fixture | yes |
| `POST /api/cockpit/holdings` | Holdings | creates holding | disposable local fixture | yes |
| `PATCH /api/cockpit/holdings/{holding_id}` | Holdings | edits holding | disposable local fixture | yes |
| `DELETE /api/cockpit/holdings/{holding_id}` | Holdings | deletes holding | disposable local fixture | yes |
| `POST /api/cockpit/marketplace/missions` | Marketplace Missions | creates mission | marketplace fixture task | yes |
| `PATCH /api/cockpit/marketplace/missions/{missionId}` | Marketplace Missions | edits mission | marketplace fixture task | yes |
| `DELETE /api/cockpit/marketplace/missions/{missionId}` | Marketplace Missions | deletes mission | marketplace fixture task | yes |
| `POST /api/cockpit/marketplace/missions/{missionId}/link-product` | Marketplace Missions | links tracked product | marketplace fixture task | yes |
| `DELETE /api/cockpit/marketplace/missions/{missionId}/link-product` | Marketplace Missions | unlinks product | marketplace fixture task | yes |
| `POST /api/cockpit/marketplace/scans` | Marketplace Scans | starts scan/background job/browser work | explicit marketplace scan task | yes |
| `POST /api/cockpit/marketplace/benchmarks/refresh` | Marketplace Price | refreshes benchmark artifacts | explicit marketplace benchmark task | yes |
| `POST /api/cockpit/marketplace/price-intelligence/calibrate` | Marketplace Price | calibrates price intelligence | explicit calibration task | yes |
| `POST /api/cockpit/marketplace/price-intelligence/tracked-products/{trackedProductId}/ebay-sync` | Marketplace Price | external eBay/runtime sync | explicit external sync approval | yes |
| `PATCH /api/cockpit/marketplace/matches/{matchId}` | Marketplace Matches | edits match state | known fixture match only | yes |
| `PATCH /api/cockpit/marketplace/matches/{matchId}/benchmark-review` | Marketplace Matches | writes benchmark review | known fixture match only | yes |
| `PATCH /api/cockpit/marketplace/alerts/{alertId}` | Marketplace Alerts | edits alert state | known fixture alert only | yes |
| `POST /api/cockpit/commentary/takeaways` | Chat/Commentary | creates or processes takeaway context | fixture plan | yes |
| `POST /api/cockpit/commentary/marketplace-capture/token` | Capture helper | generates capture token/session context | capture task approval | yes |
| `POST /api/cockpit/commentary/marketplace-capture/submit` | Capture helper | ingests marketplace snapshot/commentary | capture task approval | yes |
| `POST /api/commentary/ingest-url` | Chat/Commentary | ingests URL content | ingestion task approval | yes |
| `POST /api/commentary/inspect-marketplace` | Chat/Marketplace | inspects external marketplace URL | external inspection approval | yes |
| `POST /rag/query` | News/RAG | retrieval/model query path; may consume runtime | fixture/provenance smoke task | yes |
| `POST /api/context/verification/run` | Verification | generates verification context | Evaluation task approval | yes |
| `POST /api/extraction-eval/real-gold?background=true` | Verification/Evaluation | starts background real-gold eval | Evaluation/Financial Truth task | yes |
| `POST /api/extraction-eval/confirmed-metric-coverage/run` | Verification/Evaluation | generates coverage review artifact | Evaluation/Financial Truth task | yes |
| `POST /api/process/document/{documentId}` | History/Verification | processes document/extraction | Financial Truth task | yes |
| `POST /api/extraction-review/session` | Verification | creates review session | Evaluation task approval | yes |
| `POST /api/extraction-review/session/{sessionId}/decision` | Verification | writes review decision | Evaluation task approval | yes |
| `POST /api/cockpit/memory/company/add` | Memory | writes company memory | Memory lane confirmation gate | yes |
| `POST /api/cockpit/memory/company/expire` | Memory | expires company memory | Memory lane confirmation gate | yes |
| `POST /api/cockpit/memory/market/add` | Memory | writes market memory | Memory lane confirmation gate | yes |
| `POST /api/cockpit/memory/market/expire` | Memory | expires market memory | Memory lane confirmation gate | yes |
| `POST /api/cockpit/memory/thesis/proposals` | Thesis/Memory | creates thesis proposal | Memory lane confirmation gate | yes |
| `POST /api/cockpit/memory/thesis/proposals/{proposalId}/apply` | Thesis/Memory | applies proposal | explicit thesis confirmation gate | yes |
| `POST /api/cockpit/memory/thesis/proposals/{proposalId}/confirm` | Thesis/Memory | confirms proposal | explicit thesis confirmation gate | yes |
| `POST /api/cockpit/memory/thesis/proposals/{proposalId}/reject` | Thesis/Memory | rejects proposal | explicit thesis confirmation gate | yes |
| `POST /api/cockpit/thesis-audit` | Thesis Audit | runs thesis audit, may use model/context | Provenance/Memory task approval | yes |
| `POST /api/cockpit/thesis-audit/alerts/{alertId}/status` | Thesis Audit | changes watchdog alert status | Memory lane confirmation gate | yes |
| `PATCH /api/cockpit/preferences` | Settings/Chat routing | changes local Cockpit preferences | fixture or explicit operator approval | yes |
| `POST /api/system/proposals/apply` | System | applies proposal/system state | system task approval | yes |
| ingestion/backfill/Qdrant sync/migrations | backend ops | mutates canonical stores or schema | separate approved task only | yes |
