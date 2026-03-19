from __future__ import annotations

from autodev.runtime.patch_debate import critique_patch, propose_patch, revise_patch


def test_propose_patch_calls_llm_with_task_and_context() -> None:
    prompts: list[str] = []

    def llm(prompt: str) -> str:
        prompts.append(prompt)
        return "proposal"

    output = propose_patch("fix bug", "repo tree", llm)
    assert output == "proposal"
    assert "Task:\nfix bug" in prompts[0]
    assert "Repository context:\nrepo tree" in prompts[0]


def test_critique_patch_calls_llm_with_patch() -> None:
    prompts: list[str] = []

    def llm(prompt: str) -> str:
        prompts.append(prompt)
        return "critique"

    output = critique_patch("fix bug", "FILE: a.py\nx = 1\n", "repo tree", llm)
    assert output == "critique"
    assert "Patch:\nFILE: a.py\nx = 1\n" in prompts[0]
    assert "Identify potential issues" in prompts[0]


def test_revise_patch_calls_llm_with_critique() -> None:
    prompts: list[str] = []

    def llm(prompt: str) -> str:
        prompts.append(prompt)
        return "revision"

    output = revise_patch("fix bug", "FILE: a.py\nx = 1\n", "missing import", "repo tree", llm)
    assert output == "revision"
    assert "Critique:\nmissing import" in prompts[0]
    assert "Return FILE blocks only." in prompts[0]
