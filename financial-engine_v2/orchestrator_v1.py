import subprocess
import time

PROJECT_ROOT = "/home/l4nd0/tenn/financial-engine_v2"


def run_command(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    return result.stdout + result.stderr


def get_status():
    return run_command("cd . && ./scripts/status.sh")


def run_codex(prompt):
    print("\n==========================")
    print("SEND THIS TO CODEX (Cursor)")
    print("==========================\n")
    print(prompt)
    input("\nPress ENTER after Codex completes...\n")
    return "Executed via Cursor"


def main():
    while True:
        print("\n==========================")
        print("SYSTEM STATUS")
        print("==========================\n")

        status = get_status()
        print(status)

        task = input("\nWhat do you want to do? (type 'exit' to stop)\n")
        if task.strip().lower() in {"exit", "quit"}:
            print("Exiting.")
            break

        codex_prompt = f"""
You are executing inside financial-engine_v2.

RULES:
- Use only scripts/
- Do not create new environments
- Backend must be on port 8000
- Do not spawn duplicate processes

TASK:
{task}

OUTPUT:
- Commands executed
- Errors (if any)
"""

        result = run_codex(codex_prompt)

        print("\n[RESULT]\n")
        print(result)

        print("\n[UPDATED STATUS]\n")
        print(get_status())

        time.sleep(1)


if __name__ == "__main__":
    main()
