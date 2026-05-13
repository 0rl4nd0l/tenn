-- DO_NOT_RUN_rollback_backend_api_expiry_100.sql
-- DO_NOT_RUN. Prefer restoring backup DB for full rollback: /mnt/hdd-data/home/l4nd0/tenn_runtime_backups/memory_interticker_cleanup_backend_api_expiry_100_20260513_051856/company_memory.sqlite.pre_backend_api_expiry_100
-- This row-id rollback restores only targeted entry statuses and summary counts.
-- It does not undo last_seen_at/closed_at timestamp mutations caused by the backend expiry API.

BEGIN IMMEDIATE;
CREATE TEMP TABLE cleanup_expire_candidate_ids(entry_id INTEGER PRIMARY KEY);
INSERT INTO cleanup_expire_candidate_ids(entry_id) VALUES
  (636),
  (637),
  (638),
  (641),
  (642),
  (643),
  (647),
  (652),
  (653),
  (655),
  (657),
  (658),
  (660),
  (661),
  (1065),
  (1066),
  (1067),
  (1068),
  (1069),
  (1070),
  (1071),
  (1072),
  (1073),
  (1074),
  (1075),
  (1076),
  (1077),
  (1079),
  (1776),
  (1777),
  (1778),
  (1779),
  (1780),
  (1781),
  (1782),
  (1783),
  (1784),
  (1785),
  (1786),
  (1787),
  (1788),
  (1789),
  (1790),
  (1791),
  (1792),
  (1793),
  (1794),
  (1795),
  (1797),
  (1798),
  (258),
  (259),
  (260),
  (263),
  (264),
  (265),
  (269),
  (274),
  (275),
  (277),
  (278),
  (279),
  (280),
  (281),
  (282),
  (811),
  (812),
  (813),
  (814),
  (815),
  (816),
  (817),
  (818),
  (819),
  (820),
  (821),
  (822),
  (823),
  (824),
  (825),
  (1697),
  (1698),
  (1699),
  (1700),
  (1701),
  (1702),
  (1703),
  (1704),
  (285),
  (286),
  (287),
  (290),
  (291),
  (292),
  (296),
  (301),
  (302),
  (304),
  (305),
  (306);

UPDATE memory_entries
SET status = 'active'
WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
  AND status = 'expired';

INSERT INTO change_log (company_id, entry_id, event_type, details_json, created_at)
SELECT
  e.company_id,
  e.entry_id,
  'rollback_expire',
  json_object(
    'source', 'historical_memory_cleanup_rollback',
    'approval_id', 'approved_by_user_20260513_backend_api_pilot_100_20260513_051856',
    'live_report', 'reports/memory_interticker_cleanup_backend_api_expiry_100_20260513_051856'
  ),
  'OPERATOR_TIMESTAMP_UTC'
FROM memory_entries e
JOIN cleanup_expire_candidate_ids c ON c.entry_id = e.entry_id;

UPDATE company_memory
SET active_entry_count = (
      SELECT COUNT(*) FROM memory_entries e
      WHERE e.company_id = company_memory.company_id AND e.status = 'active'
    ),
    updated_at = 'OPERATOR_TIMESTAMP_UTC'
WHERE company_id IN (
  SELECT DISTINCT company_id FROM memory_entries
  WHERE entry_id IN (SELECT entry_id FROM cleanup_expire_candidate_ids)
);

COMMIT;
