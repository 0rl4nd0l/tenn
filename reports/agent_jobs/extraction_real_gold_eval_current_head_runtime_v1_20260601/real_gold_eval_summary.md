# Extraction Real Eval Summary

- Generated: 2026-06-01T10:02:50.415758Z
- Dataset: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data/extraction_gold_real`
- Documents: 15
- Eval mode: `canonical`
- KPI eligible: yes

## Eval Policy

- Policy version: `2026-04-20`
- Dataset commit: `24cfc90bc5a1e055adc7b8349f936be368d8d786`
- Dataset content hash: `ff4501e04ec27354fa9dfa9f3791e88ac769ad90351fbb9b0bd3339c39236ba7`
- Dataset dirty: `False`

## Total Accuracy

- Metric accuracy: 87.18% (34/39)
- Context accuracy: 93.33% (14/15)
- Trust matches expected: 12/15

## Artifact Outputs

| Artifact | Path |
| --- | --- |
| canonical_scorecard_json | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_canonical_scorecard.json` |
| documents_csv | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_documents.csv` |
| metrics_csv | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_metrics.csv` |
| results_json | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results.json` |
| summary_json | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_summary.json` |
| summary_markdown | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_summary.md` |
| trust_triggers_csv | `reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_trust_triggers.csv` |

## Trust Distribution

| Trust outcome | Count |
| --- | ---: |
| trusted | 12 |
| abstain | 2 |
| quarantine | 1 |

## Trust Trigger Summary

| Trigger | Count |
| --- | ---: |
| context_mismatch:period_end | 1 |
| net_debt:missing | 1 |
| net_debt:wrong | 1 |

## Per-Metric Failure Counts

| Metric | Wrong | Missing | Abstain |
| --- | ---: | ---: | ---: |
| revenue | 0 | 0 | 0 |
| operating_cash_flow | 0 | 0 | 0 |
| net_debt | 1 | 1 | 0 |

## Most Failed Documents

| Document | Ticker | Period | Trust | Failed metrics | Context mismatches |
| --- | --- | --- | --- | ---: | ---: |
| 29m_a_2025-12-31 | 29M | A 2025-12-31 | abstain | 1 | 0 |
| a2m_h_2025-12-31 | A2M | H 2025-12-31 | abstain | 1 | 0 |
| 14d_q_2021-03-31 | 14D | Q 2021-03-31 | quarantine | 0 | 1 |
| 10x_q_2025-12-31_difficult | 10X | Q 2025-12-31 | trusted | 0 | 0 |
| bhp_a_2021-06-30_difficult | BHP | A 2021-06-30 | trusted | 0 | 0 |
| bhp_a_2025-06-30 | BHP | A 2025-06-30 | trusted | 0 | 0 |
| eqr_q_2025-12-31 | EQR | Q 2025-12-31 | trusted | 0 | 0 |
| gre_q_2024-12-31 | GRE | Q 2024-12-31 | trusted | 0 | 0 |
| gre_q_2025-09-30 | GRE | Q 2025-09-30 | trusted | 0 | 0 |
| min_h_2025-12-31 | MIN | H 2025-12-31 | trusted | 0 | 0 |
| qbe_h_2025-06-30 | QBE | H 2025-06-30 | trusted | 0 | 0 |
| rio_a_2023-12-31 | RIO | A 2023-12-31 | trusted | 0 | 0 |
| rio_a_2024-12-31 | RIO | A 2024-12-31 | trusted | 0 | 0 |
| rms_h_2025-12-31 | RMS | H 2025-12-31 | trusted | 0 | 0 |
| tls_h_2025-12-31 | TLS | H 2025-12-31 | trusted | 0 | 0 |

## Per-Document Breakdown

| Document | Ticker | Period | Context | Trust (actual / expected) | Metric statuses | Mismatch reasons |
| --- | --- | --- | --- | --- | --- | --- |
| 10x_q_2025-12-31_difficult | 10X | Q 2025-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| 14d_q_2021-03-31 | 14D | Q 2021-03-31 | mismatch | quarantine / trusted | revenue:quarantine, operating_cash_flow:quarantine, net_debt:quarantine | period_end: expected='2021-03-31' actual=None; metric:revenue:Context mismatch; fixture marked quarantine; metric:operating_cash_flow:Context mismatch; fixture marked quarantine; metric:net_debt:Context mismatch; fixture marked quarantine; trust: expected=trusted actual=quarantine; extraction_error:validation_gate:missing_period_end |
| 29m_a_2025-12-31 | 29M | A 2025-12-31 | ok | abstain / trusted | revenue:correct, operating_cash_flow:correct, net_debt:missing | metric:net_debt:Expected metric was absent; trust: expected=trusted actual=abstain |
| a2m_h_2025-12-31 | A2M | H 2025-12-31 | ok | abstain / trusted | revenue:correct, operating_cash_flow:correct, net_debt:wrong | metric:net_debt:Expected null was not null; trust: expected=trusted actual=abstain |
| bhp_a_2021-06-30_difficult | BHP | A 2021-06-30 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| bhp_a_2025-06-30 | BHP | A 2025-06-30 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| eqr_q_2025-12-31 | EQR | Q 2025-12-31 | ok | trusted / trusted | operating_cash_flow:correct | - |
| gre_q_2024-12-31 | GRE | Q 2024-12-31 | ok | trusted / trusted | operating_cash_flow:correct | - |
| gre_q_2025-09-30 | GRE | Q 2025-09-30 | ok | trusted / trusted | operating_cash_flow:correct | extraction_error:validation_gate:low_confidence:0.4 |
| min_h_2025-12-31 | MIN | H 2025-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| qbe_h_2025-06-30 | QBE | H 2025-06-30 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| rio_a_2023-12-31 | RIO | A 2023-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| rio_a_2024-12-31 | RIO | A 2024-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| rms_h_2025-12-31 | RMS | H 2025-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
| tls_h_2025-12-31 | TLS | H 2025-12-31 | ok | trusted / trusted | revenue:correct, operating_cash_flow:correct, net_debt:correct | - |
