## Summary

Refs #282.

- normalize compact formatting in `financial-engine_v2/backend/app/api/routes.py`
- expand compact dictionary returns for readability
- remove an unused `Optional` import and place logger initialization after imports

## Validation

- `py_compile routes.py` => passed
- `ruff format --check routes.py` => passed
- `ruff check routes.py` => passed
- focused route tests => 19 passed, 5 existing warnings
- `git diff --check` => passed
- task-card validate / overlap / claim => passed

## Safety

- formatting-only source cleanup
- no runtime/service start
- no DB/Qdrant/Redis/news/memory/source-PDF/gold-label/model/service config
  mutation
- no route behavior, dependency, or UI change
