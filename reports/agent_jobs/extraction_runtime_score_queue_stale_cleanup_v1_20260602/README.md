# Extraction Runtime Score Queue Stale Cleanup V1

## Result

Completed controlled Redis score-queue cleanup. Removed exactly 32 pre-snapshot `thesis_watchdog_check` messages by serialized payload hash using `LREM score 1 <payload>`. Preserved 0 messages.

No extraction, backfill, canary execution, bounded broad sample, backend start, worker start, router start, DB mutation, Qdrant mutation, news mutation, or memory mutation was run by this task.

## Queue Lengths

| Queue | Before | After |
| --- | ---: | ---: |
| score | 32 | 0 |
| ingest | 0 | 0 |
| embed | 0 | 0 |
| llm_gpu | 0 | 0 |
| llm_cpu | 0 | 0 |

Unacked keys before: `[]`

Unacked keys after: `[]`

## Readiness Verdict

Bounded broad sample can now be requested separately: `true`.

Evidence:

- Redis queues after cleanup are all zero.
- No `*unacked*` Redis keys remain.
- No backend, worker, broad extraction, backfill, process-document, or extraction-eval process matched the post-check `/proc` scan.
- Ports `8000`, `8001`, and `8002` are closed.
- `scripts/gpu_process_guard.sh --check` exited `0`.
- `nvidia-smi` reported Tesla M40 memory used as `0 MiB`.
- Shared registry immediately after this cleanup claim was released reported `active_jobs: []`.

Latest live-registry recheck: `[]`. The next sample task must still recheck registry state before running.

## Removed Messages

| Index | Task ID | Ticker | Title | Document ID | Raw SHA-256 prefix |
| ---: | --- | --- | --- | --- | --- |
| 0 | `0af4ccce-7b8e-439c-b067-2b2ce621128c` | `ABC` | Low confidence periodic | `6d73f250-a5e8-42b0-b35e-f6b8441e6416` | `a63d9970ea4b` |
| 1 | `9ee42094-8915-4448-9a41-1a90e2c97675` | `` | Invalid ticker doc | `5bc1f084-d843-4af7-bb61-86e89c310c88` | `2dd3db37351a` |
| 2 | `abbe3f33-624a-48e8-9352-922c63649e31` | `ABC` | Valid doc | `b58e9de2-cd96-4cf2-8e1f-411aca2001f8` | `4c61a1093324` |
| 3 | `da433c93-daa6-488e-8dfc-f2a2fc0f038e` | `ABC` | Low confidence periodic | `68eb041e-20e7-403f-af8b-6a2d3a448d9a` | `52dc230ed2f8` |
| 4 | `89113d9e-ca9e-42ca-acd5-6499041676b8` | `` | Invalid ticker doc | `84faf544-5450-4de0-8ecf-358010205c0c` | `2db3b833bb6b` |
| 5 | `18e682c0-e48e-4bb6-b26a-52e8822dd5cb` | `ABC` | Valid doc | `dd695a89-49f1-4289-8e4b-52293adc8856` | `f1a1d5310c88` |
| 6 | `6e420d95-a81e-40a4-a0c6-38340e8add16` | `CTM` | Financial Report 31 December 2025 | `035c6758-7aed-41a6-9e84-ad154125d431` | `08adacdbb486` |
| 7 | `cc58616b-ce1c-464f-8c9e-8715770b4865` | `CLV` | Clover 1H FY26 Results Announcement | `da9f9ea5-6596-464f-af14-5acf12f9b050` | `8b34c5d608a4` |
| 8 | `2573b00d-b492-4cfd-baf3-055a3e65797a` | `CRS` | Half Year Financial Report | `b43a16fb-7660-4bf7-96ab-0db641cd4032` | `6cd6d4941007` |
| 9 | `74943772-28e5-4d22-a9ca-348d48967568` | `AQX` | HALF-YEAR FINANCIAL REPORT - 31 DECEMBER 2025 | `0ed0104f-f29a-4068-8ff7-370f14fead98` | `2f4254fe61bf` |
| 10 | `43c4b366-3365-4a53-b5da-dc96c1181590` | `AM5` | Interim Financial Report - Half Year Ended 31 December 2025 | `aacc4c29-3089-48cf-8b82-8004134f9387` | `665b948f7c62` |
| 11 | `43b38118-6018-42d0-a47d-9ed0683168cc` | `ATM` | Full Year Statutory Accounts | `96e9aabd-44dc-4c2c-be8c-74248a0a9025` | `bcf562d01018` |
| 12 | `d7444db2-a98f-4af9-a743-7bde27919ead` | `AAU` | Annual Report and Full Year Statutory Accounts | `508fc892-ae88-45ec-981f-cd9e124c8375` | `f9efe8d5843e` |
| 13 | `4edbd6b6-e33c-438f-bde2-8286e1a9de47` | `CTM` | Financial Report 31 December 2025 | `035c6758-7aed-41a6-9e84-ad154125d431` | `e8f7b1d0d811` |
| 14 | `2da240a1-132f-47ca-9e6f-0df9ae11c019` | `CLV` | Clover 1H FY26 Results Announcement | `da9f9ea5-6596-464f-af14-5acf12f9b050` | `809514b7e9b2` |
| 15 | `8e0b2e8d-c779-4af6-82f5-9cfd43b69e4c` | `CRS` | Half Year Financial Report | `b43a16fb-7660-4bf7-96ab-0db641cd4032` | `5cd047722448` |
| 16 | `2d72751f-d0f1-4331-bd16-2fb5216d9e4d` | `AQX` | HALF-YEAR FINANCIAL REPORT - 31 DECEMBER 2025 | `0ed0104f-f29a-4068-8ff7-370f14fead98` | `7d1bed7265f6` |
| 17 | `4f74a6e6-0949-49a1-90fc-e7aba9f2a62b` | `AM5` | Interim Financial Report - Half Year Ended 31 December 2025 | `aacc4c29-3089-48cf-8b82-8004134f9387` | `0ce530ca37dd` |
| 18 | `d871fcd0-d5fb-4666-9320-897e9ec12c56` | `ATM` | Full Year Statutory Accounts | `96e9aabd-44dc-4c2c-be8c-74248a0a9025` | `8f5de98750f2` |
| 19 | `dfbd9bb4-f9ee-4b72-8b0f-0bc4406fe9d6` | `AAU` | Annual Report and Full Year Statutory Accounts | `508fc892-ae88-45ec-981f-cd9e124c8375` | `582acd7658f6` |
| 20 | `c2f6f69a-7d03-4113-bb9b-987300859855` | `ABC` | Low confidence doc | `13b9eb9d-9af1-4d55-a6ea-634b859879ca` | `606ad8271ecd` |
| 21 | `90820556-5fd8-4ead-8853-143518fa1527` | `ABC` | Low confidence doc | `8934af28-f4a8-45d4-9660-e92cd34ccdf1` | `82b804641775` |
| 22 | `cabc4026-6bc9-4569-9901-9ebae75bda99` | `CTM` | Financial Report 31 December 2025 | `035c6758-7aed-41a6-9e84-ad154125d431` | `df2552929300` |
| 23 | `26ffc5b0-43b5-4905-83e5-4fcb083df3d1` | `CLV` | Clover 1H FY26 Results Announcement | `da9f9ea5-6596-464f-af14-5acf12f9b050` | `b72af4ea982a` |
| 24 | `85be54b6-7a99-4c41-a45a-5f3863d9e606` | `CRS` | Half Year Financial Report | `b43a16fb-7660-4bf7-96ab-0db641cd4032` | `573bb80117a7` |
| 25 | `7fbeb496-e39d-4a5d-9942-47a0a87f7f15` | `AQX` | HALF-YEAR FINANCIAL REPORT - 31 DECEMBER 2025 | `0ed0104f-f29a-4068-8ff7-370f14fead98` | `c56b1992256b` |
| 26 | `7719ec5c-460e-42f6-9eee-f904fb220d58` | `AM5` | Interim Financial Report - Half Year Ended 31 December 2025 | `aacc4c29-3089-48cf-8b82-8004134f9387` | `974eaf87d910` |
| 27 | `dbac2a07-c536-4dbb-bf35-93ce39ac7866` | `ATM` | Full Year Statutory Accounts | `96e9aabd-44dc-4c2c-be8c-74248a0a9025` | `4ad4a1115bbd` |
| 28 | `0ac66bcd-496f-4d47-a4f6-727eae11cf50` | `AAU` | Annual Report and Full Year Statutory Accounts | `508fc892-ae88-45ec-981f-cd9e124c8375` | `8b97759365a4` |
| 29 | `cf8cc5a7-a638-47da-ab89-4afd0bdf3b70` | `ABC` | Low confidence doc | `a35dca7b-102c-43cb-a4b8-6836d9ca039c` | `f3b9cf2c490a` |
| 30 | `468a8631-2231-4a90-9338-b2c957b0e6cb` | `ABC` | Low confidence doc | `0cb02ca7-bf4e-4bbd-b29e-e223ad77ac0f` | `6de60a90cf85` |
| 31 | `82218a30-c706-4014-8ee7-3d0678e72d92` | `ABC` | Low confidence doc | `e64e8392-9b59-4a52-ab8b-a8bfade24f76` | `8c4989b506da` |

## Preserved Messages

None.

## DATA_MISSING

- Requested prior readiness audit directory is absent in this checkout: `reports/agent_jobs/extraction_runtime_score_queue_readiness_audit_v1_20260602`.
- Redis/Celery score messages do not include enqueue timestamps, so staleness is established from dead producer PIDs, no active owners, no workers, and no unacked keys rather than message age.

## Artifacts

- `pre_cleanup_score_queue_snapshot.json`
- `post_cleanup_score_queue_snapshot.json`
- `status.json`
- `diff-check.json` after task-card check-diff
