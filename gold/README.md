# Gold Set Format

Each gold document label must live at:

- `gold/<TICKER>/<doc_id>.json`

Required top-level fields:

- `doc_id`
- `ticker`
- `pdf_sha256`
- `published_at`
- `fields` (array)

Each entry in `fields` requires:

- `metric`
- `period_end`
- `period_type`
- `value`
- `unit_scale`
- `currency`
- `scope`

Optional field-level fields:

- `statement_type`
- `source_hint`

Use `scripts/bootstrap_gold_templates.py` to generate starter templates from canonical CSV.
Score with:

```bash
/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python scripts/score_gold_set.py \
  --gold-dir gold \
  --canonical-csv <canonical_csv> \
  --out-dir <out_dir>
```
