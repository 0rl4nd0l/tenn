"""Fail-closed quarantine for the deprecated legacy worker task module.

This module intentionally registers no Celery tasks. The canonical worker
surface is ``financial-engine_v2/backend/app/worker_tasks.py``.

See ``docs/architecture/SYSTEM_CONTRACT.md`` section 6.2.
"""

raise RuntimeError(
    "financial-engine_v2/worker/app/tasks.py is DEPRECATED and MUST NOT RUN; "
    "use financial-engine_v2/backend/app/worker_tasks.py instead."
)
