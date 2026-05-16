# news_loader_ollama_url_hardening_integrate_nvme_v1_20260515

Integrated committed loader hardening `a1802c757b54` into the active NVMe worktree.

## Scope

- Added explicit Ollama URL resolution controls to `scripts/load_news_to_qdrant.py`.
- Added focused unit coverage in `financial-engine_v2/backend/tests/test_load_news_to_qdrant.py`.
- Did not run live news sync, mutate DB/Qdrant, restart runtime, build Docker, or touch rented GPU/APEX workflows.

## Validation

- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/scripts:$PWD" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_load_news_to_qdrant.py -q` -> 5 passed.
- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/scripts:$PWD" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/load_news_to_qdrant.py financial-engine_v2/backend/tests/test_load_news_to_qdrant.py` -> All checks passed.
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m py_compile scripts/load_news_to_qdrant.py` -> passed.
- `git diff --check` -> passed.
- `git diff --cached --check` -> passed.
