"""Thin OpenClaw-style control agent for AutoDev."""

from __future__ import annotations

import subprocess
import sys

try:
    from openclaw.nl_router import route_user_message
except ModuleNotFoundError:
    from nl_router import route_user_message

try:
    from openclaw.task_generator import (
        append_task,
        extract_task_request_text,
        generate_task_from_text,
        is_dangerous_task_request,
        is_task_request,
    )
except ModuleNotFoundError:
    from task_generator import (
        append_task,
        extract_task_request_text,
        generate_task_from_text,
        is_dangerous_task_request,
        is_task_request,
    )


CONTROL_CMD = [sys.executable, "-m", "autodev.runtime.control"]
EXIT_ALIASES = {"exit", "quit", "q"}

CONTROL_ACTIONS = {
    "run": ("run-once",),
    "status": ("status",),
    "latest": ("latest-report",),
    "runs": ("list-runs",),
    "report": ("tail", "--file", "report"),
    "gates": ("tail", "--file", "gates"),
    "start": ("start",),
    "stop": ("stop",),
}

HELP = """
Commands:

run      -> run next task
status   -> show daemon status
latest   -> show latest run
runs     -> list runs
report   -> show latest report
gates    -> show gate logs
start    -> start daemon
stop     -> stop daemon
help     -> show commands
exit     -> quit
quit/q   -> quit
"""

STARTUP_BANNER = """
--------------------------------
OpenClaw Natural Language Mode
You can type requests like:

"run the next task"
"what is the system doing"
"show me the last report"
"start autonomous mode"
"optimize the pdf parser"
"add tests for financial engine"
"task improve the financial feature pipeline"
"run daily news ingestion and verify outputs"
"run news pipeline tests and report results"
"run backfill and report failures"

LLM router:
OPENCLAW_ROUTER_PROVIDER=auto|ollama|openai|llamacpp|none
OPENCLAW_ROUTER_OLLAMA_MODEL=deepseek-coder:6.7b
OPENCLAW_ROUTER_OPENAI_MODEL=gpt-4.1-mini
OPENCLAW_ROUTER_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_API_KEY=local-openai-key (for local llama.cpp any non-empty value works)
--------------------------------
"""

UNKNOWN_MESSAGE = """
I didn't understand that request.
Use a command (run/status/latest/runs/report/gates/start/stop/help)
or create a task with a request like:
- optimize the pdf parser
- add tests for financial engine
- run news ingestion and run news tests
- operation-formats are schema-based: operation, goal, checks, outputs, constraints
Tip: use `task <description>` to force task creation.
"""


def run_control(args: tuple[str, ...]) -> None:
    cmd = CONTROL_CMD + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def main() -> None:
    print(STARTUP_BANNER.strip())
    print(HELP.strip())
    while True:
        user_input = input("openclaw> ").strip()
        normalized = user_input.lower()

        if not normalized:
            continue

        if normalized in EXIT_ALIASES:
            break

        decision = route_user_message(user_input)
        action = decision["action"]

        if action == "unknown":
            print(UNKNOWN_MESSAGE.strip())
            continue

        if action == "task":
            raw_task_text = decision.get("task_text") or user_input
            task_text = extract_task_request_text(raw_task_text)
            if is_dangerous_task_request(task_text):
                print("Request rejected for safety.")
                print("Blocked terms: delete, rm, format disk, shutdown, system")
                continue
            if action != "task" and not is_task_request(task_text):
                print(UNKNOWN_MESSAGE.strip())
                continue
            print("Interpreting request as: task")
            print("Creating AutoDev task...")
            task_line = generate_task_from_text(task_text)
            append_task(task_line)
            print("Task created:")
            print(task_line)
            print("Running AutoDev...")
            print("Interpreting request as: run")
            run_control(CONTROL_ACTIONS["run"])
            continue

        command = action
        print(f"Interpreting request as: {command}")

        if command == "help":
            print(HELP.strip())
            continue

        if command in CONTROL_ACTIONS:
            run_control(CONTROL_ACTIONS[command])


if __name__ == "__main__":
    main()
