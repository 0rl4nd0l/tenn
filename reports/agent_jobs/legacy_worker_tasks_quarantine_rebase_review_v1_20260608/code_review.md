{
  "status": "SUCCESS",
  "work_log": {
    "assumptions": [
      "Review scope is the staged replay diff for financial-engine_v2/worker/app/tasks.py and financial-engine_v2/backend/tests/test_architecture_invariants.py."
    ],
    "sources_used": [
      "git diff --cached",
      "financial-engine_v2/worker/app/tasks.py",
      "financial-engine_v2/backend/tests/test_architecture_invariants.py",
      "focused validation outputs"
    ],
    "files_read": [
      "financial-engine_v2/worker/app/tasks.py",
      "financial-engine_v2/backend/tests/test_architecture_invariants.py"
    ],
    "files_modified": [],
    "validation_checks": [
      "python3 -m py_compile financial-engine_v2/worker/app/tasks.py financial-engine_v2/backend/tests/test_architecture_invariants.py",
      "static fail-closed import probe",
      "pytest financial-engine_v2/backend/tests/test_architecture_invariants.py -q",
      "financial-engine_v2/scripts/test_celery_task_registration_smoke.py",
      "ruff check financial-engine_v2/worker/app/tasks.py financial-engine_v2/backend/tests/test_architecture_invariants.py"
    ]
  },
  "result": {
    "critical": [],
    "warnings": [],
    "suggestions": []
  }
}
