## Summary

Refs #254.

- truth-label the chat learning loop as partially active: quality scoring
  telemetry is wired, but live `/chat` traffic does not write
  `chat_preferences.json`
- document that the preference updater requires fully shaped records with
  `financial_task_type`, `retrieval_params`, and `router_role`
- add focused updater coverage proving runtime-shaped session records do not
  learn retrieval/router preferences without those fields

## Validation

- `pytest test_chat_preference_updater.py` => 5 passed
- `ruff format --check` touched Python test => passed
- `ruff check` touched Python test => passed
- `py_compile` touched Python test => passed
- doc truth-label grep => passed
- `git diff --check` => passed
- task-card validate / overlap / claim => passed

## Safety

- no runtime/service start
- no DB/Qdrant/Redis/news/memory/source-PDF/gold-label/model/service config
  mutation
- no hidden preference writer wiring
- no live runtime functionality claim; this is a docs/test truth-label fix
