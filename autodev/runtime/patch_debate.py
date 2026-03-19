"""Prompt helpers for proposer/skeptic/auditor patch debate."""

from __future__ import annotations

from typing import Callable


LLMFn = Callable[[str], str]


def propose_patch(task: str, repo_context: str, llm: LLMFn) -> str:
    prompt = f"""
You are a senior engineer.

Task:
{task}

Repository context:
{repo_context}

Generate file edits using FILE blocks.
""".strip()
    return llm(prompt)


def critique_patch(task: str, patch: str, repo_context: str, llm: LLMFn) -> str:
    prompt = f"""
You are reviewing a proposed code change.

Task:
{task}

Patch:
{patch}

Repository context:
{repo_context}

Identify potential issues:
- missing imports
- broken tests
- edge cases
- performance issues
""".strip()
    return llm(prompt)


def revise_patch(task: str, patch: str, critique: str, repo_context: str, llm: LLMFn) -> str:
    prompt = f"""
You are an auditing engineer.

Original task:
{task}

Patch:
{patch}

Critique:
{critique}

Repository context:
{repo_context}

Rewrite the patch to address the critique.
Return FILE blocks only.
""".strip()
    return llm(prompt)
