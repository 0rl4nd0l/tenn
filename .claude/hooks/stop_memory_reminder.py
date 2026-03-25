#!/usr/bin/env python3
"""Stop hook: remind Claude to save session memories.

Layer 1 (diff-aware): inspects changed files to detect significant subsystem
changes and prompts Claude to record the *why* behind them.

Layer 2 (generic): always reminds Claude to save any feedback, user preferences,
or project state changes discovered during the session.
"""
import json
import os
import subprocess

REPO = "/home/l4nd0/tenn"
MEMORY_DIR = os.path.expanduser(
    "~/.claude/projects/-home-l4nd0-tenn/memory"
)

# Subsystem patterns → human-readable labels
SUBSYSTEMS = {
    "extraction": {
        "patterns": ["extraction", "multipass", "docling", "build_prompt"],
        "label": "Extraction pipeline",
    },
    "rag": {
        "patterns": ["rag", "retriev", "hybrid_retriever", "reranker", "qdrant"],
        "label": "RAG / retrieval",
    },
    "embeddings": {
        "patterns": ["embedding", "vector", "qdrant", "nomic"],
        "label": "Embeddings / vector store",
    },
    "ingestion": {
        "patterns": ["pipeline.py", "pipeline_service", "ingest", "backfill"],
        "label": "Ingestion pipeline",
    },
    "cockpit": {
        "patterns": ["cockpit/core", "cockpit/ui", "cockpit/integrations", "agent_loop"],
        "label": "Cockpit / agent system",
    },
    "model_routing": {
        "patterns": ["model_rout", "router.py", "router_optimizer", "hybrid_router"],
        "label": "Model routing",
    },
    "llm_infra": {
        "patterns": ["llamacpp", "ollama", "llama_server", "run_llama"],
        "label": "LLM infrastructure",
    },
    "governance": {
        "patterns": ["SYSTEM_CONTRACT", "CLAUDE.md", "AGENTS.md", "architecture/"],
        "label": "System governance / architecture docs",
    },
    "hooks_config": {
        "patterns": ["settings.json", ".mcp.json", "hooks/", "commands/", "skills/"],
        "label": "Agent hooks / config / skills",
    },
    "news": {
        "patterns": ["newspaper", "news_", "sources_", "news_substrate"],
        "label": "News substrate",
    },
}


def get_changed_files():
    """All files changed vs HEAD + untracked."""
    os.chdir(REPO)
    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True,
    ).stdout
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True,
    ).stdout
    all_files = set(
        f for f in (diff + "\n" + staged + "\n" + untracked).splitlines() if f
    )
    return all_files


def detect_subsystems(changed_files):
    """Return set of subsystem labels touched by changed files."""
    touched = set()
    for f in changed_files:
        fl = f.lower()
        for key, info in SUBSYSTEMS.items():
            if any(p in fl for p in info["patterns"]):
                touched.add(info["label"])
    return sorted(touched)


def build_message(changed_files, touched_subsystems):
    """Build the systemMessage for Claude."""
    parts = []

    # --- Layer 1: diff-aware ---
    if touched_subsystems:
        parts.append("MEMORY CHECK — Significant subsystems changed this session:")
        for sub in touched_subsystems:
            parts.append(f"  • {sub}")
        parts.append("")
        parts.append(
            "For each subsystem above, consider saving a PROJECT memory if:"
        )
        parts.append("  - A decision was made (and why)")
        parts.append("  - A blocker was discovered or resolved")
        parts.append("  - State changed in a way the next session needs to know")
        parts.append(
            "  - The change was non-obvious and the 'why' isn't in the commit message"
        )
        parts.append("")

    # --- Layer 2: generic (always) ---
    parts.append("SESSION MEMORY CHECKLIST — Before ending, save memories if any apply:")
    parts.append("  • FEEDBACK: Did the user correct your approach or confirm a non-obvious choice?")
    parts.append("  • USER: Did you learn something new about the user's role, preferences, or expertise?")
    parts.append("  • PROJECT: Did project state change (blockers, decisions, sprint progress)?")
    parts.append("  • REFERENCE: Did the user point to an external resource (Linear, Slack, dashboard)?")
    parts.append("")
    parts.append(
        "Skip if nothing new was learned. Do not save duplicates — check MEMORY.md first."
    )

    return "\n".join(parts)


def main():
    try:
        changed = get_changed_files()
        touched = detect_subsystems(changed)
        msg = build_message(changed, touched)
        print(json.dumps({"systemMessage": msg}))
    except Exception:
        # Hook must never block session exit
        pass


if __name__ == "__main__":
    main()
