# Autonomous Delegation with OpenCode

This guide explains how to set up and manage autonomous delegation tasks using the OpenCode CLI. OpenCode acts as a specialized worker agent for feature implementation, refactoring, and PR reviews.

## 1. Core Architecture

In this workspace, the delegation of duties is strictly split by provider and CLI tool to leverage specialized strengths:

| Tool | Focus & Subscription | Primary Responsibility |
| :--- | :--- | :--- |
| **Claude CLI (Claude Code)** | Native Claude Subscription | **High-Stakes Reasoning**: Complex architecture, deep logic refactoring, and state-management debugging. |
| **Gemini CLI (This Agent)** | Gemini Pro/Flash | **UI, Architecture & Strategy**: Frontend (React/Tailwind), repo-wide analysis, high-context planning, and visual consistency. |
| **OpenCode CLI** | **Codex Pro** & **Ollama Cloud** | **Backend & Automation**: Python/Node implementation, API design, unit tests, and repetitive boilerplate. |

## 2. Delegation Strategy

According to user requirements, work should be routed as follows:

### A. Claude Native Sessions
When a task requires Anthropic's specific reasoning strengths or native tool integration:
- **Usage**: Launch a native `claude` CLI session.
- **Workflow**: `claude -- "Implement the core logic for the forecasting engine"`

### B. Gemini CLI (Orchestrator)
When a task requires high context or visual/frontend expertise:
- **Usage**: Handled directly by this agent (Gemini CLI).
- **Mandate**: Utilize **subagents** (`codebase_investigator`, `generalist`) for complex research or batch tasks to maintain orchestrator context efficiency.

### C. OpenCode (Codex & Free Models)
When a task involves implementation or routine automation, choose the appropriate agent to save tokens:

| Agent | Model Tier | Task Type |
| :--- | :--- | :--- |
| `backend` | **Codex Pro** | Core backend logic, complex API design. |
| `fast` | **Codex Mini** | Quick fixes, unit tests, rapid scaffolding. |
| `free` | **Ollama Cloud** | Routine automation, bulk refactors, low-stakes tasks. |
| `lite` | **Gemini Lite** | Documentation, simple docstrings, and linting. |

- **Usage**: `scripts/opencode-server start` + delegation tasks.
- **Workflow**: `opencode run "Implement the auth endpoints" --agent backend`

## 3. Delegation Workflows

### A. Shared Server Workflow (Preferred)
The project uses a dedicated management script for a shared OpenCode server. This allows multiple clients (TUI, background workers, or even this Orchestrator) to connect to the same persistent process.

| Command | Action |
| :--- | :--- |
| `scripts/opencode-server start` | Launches a persistent headless server on port 4096. |
| `scripts/opencode-server attach` | Connects an interactive TUI to the running server. |
| `scripts/opencode-server status` | Verifies the server is running and shows its PID/URL. |
| `scripts/opencode-server stop` | Gracefully shuts down the server. |

**Benefits**: Persists context across TUI sessions, allows attaching multiple TUIs for shared work, and provides a stable endpoint for background tasks.

### B. One-Shot Implementation (`opencode run`)
Best for well-defined, bounded tasks. If the server is running, use the attach flag:
- **Execution**: `opencode run --attach http://127.0.0.1:4096 --dir ./financial-engine_v2 "Implement JWT refresh logic"`
- **With Context**: `opencode run "Refactor this component" -f cockpit-ui/app/page.tsx`
- **With Thinking**: `opencode run "Debug latency" --thinking`

### C. Background Interactive Sessions
Best for complex tasks requiring iteration where the shared server is NOT used.
1. **Start**: `opencode --background --pty` (returns a `session_id`).
2. **Monitor**: `opencode log --session <id>` to see the worker's progress.
3. **Interact**: `opencode submit --session <id> "Now add error handling."`
4. **Finalize**: Summarize the result back to the Orchestrator.

### C. GitHub / PR Reviews
Specialized for pull request management.
- **Review**: `opencode pr 123` (checkouts the branch and starts an autonomous review).
- **Automation**: Use `opencode run "Review PR vs main" -f $(git diff origin/main --name-only)` for custom review logic.

## 4. Permissions & Sandboxing

OpenCode uses a granular permission system (`allow`, `ask`, `deny`).

- **External Directories**: Currently configured to allow access to specific skill directories (e.g., `~/.claude/skills/`).
- **Sensitive Files**: `.env` files are set to `ask` by default to prevent credential leakage.
- **Working Directory**: To avoid collisions, always scope OpenCode to a specific subdirectory or a temporary git worktree.
  - `opencode run "task" --dir ./financial-engine_v2`

## 5. Extending with MCP (Model Context Protocol)

You can give OpenCode access to external tools by adding them to `opencode.json` or using the `mcp` command.
- **Add Server**: `opencode mcp add <name> <url/command>`
- **Current Servers**: `jam` (https://mcp.jam.dev/mcp) is already connected.

## 6. Monitoring & Cost Control

- **Stats**: `opencode stats` shows usage across models and timeframes.
- **Sessions**: `opencode session list` to track active or past delegation tasks.
- **Cleanup**: `opencode session delete <id>` or `opencode session prune`.

## 7. Safety Best Practices

1. **Dry-Run first**: Use `opencode run "task" --pure` to run without external plugins.
2. **Verify changes**: Always run project-specific tests (`financial-engine_v2/.venv/bin/pytest`) after OpenCode completes a task.
3. **Commit often**: Use git to stage OpenCode's changes and review them before committing.
