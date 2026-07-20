from __future__ import annotations

import json
import multiprocessing
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import app.tasks.news_tasks as news_tasks
import pytest
from app.services import news_memo_outcomes
from app.services.news_memo_outcomes import (
    NewsMemoOutcomeStore,
    load_news_memo_outcomes,
)


def test_extract_news_memo_task_uses_news_memo_extractor(monkeypatch, tmp_path: Path):
    extractor_inits: list[dict[str, str | None]] = []
    extractor_calls: list[dict[str, str]] = []

    class StubExtractor:
        def __init__(
            self,
            *,
            llm_url=None,
            llm_model=None,
            memos_path=None,
            max_article_chars=None,
        ):
            extractor_inits.append(
                {
                    "llm_url": llm_url,
                    "llm_model": llm_model,
                    "memos_path": memos_path,
                    "max_article_chars": max_article_chars,
                }
            )

        def extract_and_store(self, **kwargs):
            extractor_calls.append(dict(kwargs))
            return {"ok": True, "source_id": kwargs["source_id"]}

    monkeypatch.setattr(news_tasks, "NewsMemoExtractor", StubExtractor)

    memos_path = tmp_path / "news_memos.jsonl"
    payload = {
        "source_id": "news:12345",
        "article_text": "BHP announces record iron ore production.",
        "provider": "newspaper4k",
        "published_at": "2026-03-30T10:00:00Z",
        "llm_url": "http://127.0.0.1:8001",
        "llm_model": "qwen2.5-14b-instruct",
        "memos_path": str(memos_path),
        "memo_skips_path": str(tmp_path / "news_memo_skips.jsonl"),
        "max_article_chars": 5000,
        "candidate_tickers": ["BHP"],
    }

    news_tasks.extract_news_memo_task.push_request(id="legacy-task-id")
    try:
        result = news_tasks.extract_news_memo_task.run(payload)
    finally:
        news_tasks.extract_news_memo_task.pop_request()

    assert extractor_inits == [
        {
            "llm_url": "http://127.0.0.1:8001",
            "llm_model": "qwen2.5-14b-instruct",
            "memos_path": str(memos_path),
            "max_article_chars": 5000,
        }
    ]
    assert extractor_calls == [
        {
            "source_id": "news:12345",
            "article_text": "BHP announces record iron ore production.",
            "provider": "newspaper4k",
            "published_at": "2026-03-30T10:00:00Z",
            "candidate_tickers": ["BHP"],
        }
    ]
    assert result == {"ok": True, "source_id": "news:12345"}
    rows = [
        json.loads(line)
        for line in memos_path.with_name("news_memo_outcomes.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows[0]["correlation_id"] == "legacy-task-id"
    assert rows[0]["task_id"] == "legacy-task-id"
    assert rows[0]["terminal_state"] == "completed"


def test_extract_news_memo_task_persists_completed_outcome(
    monkeypatch, tmp_path: Path
) -> None:
    class StubExtractor:
        def __init__(self, **_kwargs):
            pass

        def extract_and_store(self, **kwargs):
            return {
                "source_id": kwargs["source_id"],
                "key_events": ["BHP reported record production."],
            }

    monkeypatch.setattr(news_tasks, "NewsMemoExtractor", StubExtractor)
    outcomes_path = tmp_path / "news_memo_outcomes.jsonl"
    payload = {
        "source_id": "news:completed",
        "article_text": "BHP reported record production.",
        "provider": "newspaper4k",
        "memos_path": str(tmp_path / "news_memos.jsonl"),
        "correlation_id": "attempt-completed",
        "attempt_started_at_utc": "2026-07-19T06:10:00+00:00",
    }

    news_tasks.extract_news_memo_task.push_request(id="task-completed")
    try:
        result = news_tasks.extract_news_memo_task.run(payload)
    finally:
        news_tasks.extract_news_memo_task.pop_request()

    assert result["source_id"] == "news:completed"
    rows = [json.loads(line) for line in outcomes_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == "attempt-completed"
    assert rows[0]["source_id"] == "news:completed"
    assert rows[0]["task_id"] == "task-completed"
    assert rows[0]["terminal_state"] == "completed"
    assert rows[0]["completed_at_utc"]
    assert rows[0]["error_class"] == ""


def test_extract_news_memo_task_persists_needs_retry_outcome(
    monkeypatch, tmp_path: Path
) -> None:
    class RetryableExtractor:
        def __init__(self, **_kwargs):
            pass

        def extract_and_store(self, **kwargs):
            return {
                "source_id": kwargs["source_id"],
                "status": "needs_retry",
                "reason": "non_substantive_output",
            }

    monkeypatch.setattr(news_tasks, "NewsMemoExtractor", RetryableExtractor)
    outcomes_path = tmp_path / "news_memo_outcomes.jsonl"
    payload = {
        "source_id": "news:retryable",
        "article_text": "ASX:BHP shares traded in a quiet market update.",
        "provider": "newspaper4k",
        "memos_path": str(tmp_path / "news_memos.jsonl"),
        "correlation_id": "attempt-retryable",
        "attempt_started_at_utc": "2026-07-19T06:10:30+00:00",
    }

    news_tasks.extract_news_memo_task.push_request(id="task-retryable")
    try:
        result = news_tasks.extract_news_memo_task.run(payload)
    finally:
        news_tasks.extract_news_memo_task.pop_request()

    assert result["status"] == "needs_retry"
    rows = [json.loads(line) for line in outcomes_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == "attempt-retryable"
    assert rows[0]["source_id"] == "news:retryable"
    assert rows[0]["task_id"] == "task-retryable"
    assert rows[0]["terminal_state"] == "needs_retry"
    assert rows[0]["reason"] == "non_substantive_output"
    assert rows[0]["completed_at_utc"]


def test_extract_news_memo_task_persists_failure_and_reraises(
    monkeypatch, tmp_path: Path
) -> None:
    class FailingExtractor:
        def __init__(self, **_kwargs):
            pass

        def extract_and_store(self, **_kwargs):
            raise RuntimeError("model response could not be parsed")

    monkeypatch.setattr(news_tasks, "NewsMemoExtractor", FailingExtractor)
    outcomes_path = tmp_path / "news_memo_outcomes.jsonl"
    payload = {
        "source_id": "news:failed",
        "article_text": "BHP market update.",
        "provider": "newspaper4k",
        "memos_path": str(tmp_path / "news_memos.jsonl"),
        "correlation_id": "attempt-failed",
        "attempt_started_at_utc": "2026-07-19T06:11:00+00:00",
    }

    news_tasks.extract_news_memo_task.push_request(id="task-failed")
    try:
        with pytest.raises(RuntimeError, match="model response could not be parsed"):
            news_tasks.extract_news_memo_task.run(payload)
    finally:
        news_tasks.extract_news_memo_task.pop_request()

    rows = [json.loads(line) for line in outcomes_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["correlation_id"] == "attempt-failed"
    assert rows[0]["source_id"] == "news:failed"
    assert rows[0]["task_id"] == "task-failed"
    assert rows[0]["terminal_state"] == "failed"
    assert rows[0]["reason"] == "worker_exception"
    assert rows[0]["error_class"] == "RuntimeError"
    assert rows[0]["completed_at_utc"]


def test_news_memo_outcomes_reconcile_latest_attempt_per_source(
    tmp_path: Path,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    store.record_terminal(
        correlation_id="completed-1",
        source_id="news:completed",
        attempt_started_at_utc="2026-07-19T01:00:00+00:00",
        task_id="task-completed",
        terminal_state="completed",
    )
    store.record_terminal(
        correlation_id="retry-1",
        source_id="news:retry",
        attempt_started_at_utc="2026-07-19T02:00:00+00:00",
        task_id="task-retry",
        terminal_state="needs_retry",
        reason="non_substantive_output",
    )
    store.record_terminal(
        correlation_id="failed-1",
        source_id="news:failed",
        attempt_started_at_utc="2026-07-19T03:00:00+00:00",
        task_id="task-failed",
        terminal_state="failed",
        reason="worker_exception",
        error_class="RuntimeError",
    )
    store.record_dispatch_failed(
        correlation_id="dispatch-failed-1",
        source_id="news:dispatch-failed",
        attempt_started_at_utc="2026-07-19T04:00:00+00:00",
        error_class="TimeoutError",
    )
    store.record_dispatch_accepted(
        correlation_id="pending-1",
        source_id="news:pending",
        attempt_started_at_utc="2026-07-19T05:00:00+00:00",
        task_id="task-pending",
    )
    store.record_terminal(
        correlation_id="latest-old",
        source_id="news:latest",
        attempt_started_at_utc="2026-07-19T06:00:00+00:00",
        task_id="task-latest-old",
        terminal_state="completed",
    )
    store.record_dispatch_accepted(
        correlation_id="latest-new",
        source_id="news:latest",
        attempt_started_at_utc="2026-07-19T07:00:00+00:00",
        task_id="task-latest-new",
    )
    store.record_terminal(
        correlation_id="outside-1",
        source_id="news:outside",
        attempt_started_at_utc="2026-07-19T08:00:00+00:00",
        task_id="task-outside",
        terminal_state="completed",
    )
    store.record_terminal(
        correlation_id="tie-a",
        source_id="news:tie",
        attempt_started_at_utc="2026-07-19T09:00:00+00:00",
        task_id="task-tie-a",
        terminal_state="completed",
    )
    store.record_terminal(
        correlation_id="tie-b",
        source_id="news:tie",
        attempt_started_at_utc="2026-07-19T09:00:00+00:00",
        task_id="task-tie-b",
        terminal_state="failed",
        reason="worker_exception",
        error_class="RuntimeError",
    )

    result = store.reconcile_latest(
        [
            "news:completed",
            "news:retry",
            "news:failed",
            "news:dispatch-failed",
            "news:pending",
            "news:latest",
            "news:tie",
            "news:no-attempt",
        ]
    )

    assert result["status"] == "ok"
    assert result["read_errors"] == 0
    assert result["counts"] == {
        "accepted-pending": 2,
        "completed": 1,
        "needs-retry": 1,
        "failed": 2,
        "dispatch-failed": 1,
        "no-attempt": 1,
    }
    pending_samples = result["samples"]["accepted-pending"]
    assert any(
        sample
        == {
            "source_id": "news:latest",
            "correlation_id": "latest-new",
            "task_id": "task-latest-new",
        }
        for sample in pending_samples
    )
    assert {
        "source_id": "news:tie",
        "correlation_id": "tie-b",
        "task_id": "task-tie-b",
    } in result["samples"]["failed"]
    assert all(
        sample["source_id"] != "news:outside"
        for samples in result["samples"].values()
        for sample in samples
    )


def test_news_memo_outcome_replays_are_idempotent(monkeypatch, tmp_path: Path) -> None:
    tick = 0

    def next_time() -> str:
        nonlocal tick
        tick += 1
        return f"2026-07-19T08:00:{tick:02d}+00:00"

    monkeypatch.setattr(news_memo_outcomes, "utc_now_iso", next_time)
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")

    first_acceptance = store.record_dispatch_accepted(
        correlation_id="idempotent-1",
        source_id="news:idempotent",
        attempt_started_at_utc="2026-07-19T08:00:00+00:00",
        task_id="task-idempotent",
    )
    replayed_acceptance = store.record_dispatch_accepted(
        correlation_id="idempotent-1",
        source_id="news:idempotent",
        attempt_started_at_utc="2026-07-19T08:00:00+00:00",
        task_id="task-idempotent",
    )
    first_terminal = store.record_terminal(
        correlation_id="idempotent-1",
        source_id="news:idempotent",
        attempt_started_at_utc="2026-07-19T08:00:00+00:00",
        task_id="task-idempotent",
        terminal_state="needs_retry",
        reason="non_substantive_output",
    )
    replayed_terminal = store.record_terminal(
        correlation_id="idempotent-1",
        source_id="news:idempotent",
        attempt_started_at_utc="2026-07-19T08:00:00+00:00",
        task_id="task-idempotent",
        terminal_state="needs_retry",
        reason="non_substantive_output",
    )

    assert replayed_acceptance["accepted_at_utc"] == first_acceptance["accepted_at_utc"]
    assert replayed_terminal["completed_at_utc"] == first_terminal["completed_at_utc"]
    rows = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert len(rows) == 1


@pytest.mark.parametrize("dispatch_failure_first", [True, False])
@pytest.mark.parametrize(
    ("terminal_state", "reason", "error_class"),
    [
        ("completed", "", ""),
        ("needs_retry", "non_substantive_output", ""),
        ("failed", "worker_exception", "ValueError"),
    ],
)
def test_worker_terminal_refines_ambiguous_dispatch_failure_in_either_order(
    tmp_path: Path,
    dispatch_failure_first: bool,
    terminal_state: str,
    reason: str,
    error_class: str,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": f"ambiguous-{terminal_state}-{dispatch_failure_first}",
        "source_id": f"news:ambiguous-{terminal_state}-{dispatch_failure_first}",
        "attempt_started_at_utc": "2026-07-20T09:15:00+00:00",
    }

    if dispatch_failure_first:
        store.record_dispatch_failed(**common, error_class="TimeoutError")
        store.record_terminal(
            **common,
            task_id="task-published-despite-client-error",
            terminal_state=terminal_state,
            reason=reason,
            error_class=error_class,
        )
    else:
        store.record_terminal(
            **common,
            task_id="task-published-despite-client-error",
            terminal_state=terminal_state,
            reason=reason,
            error_class=error_class,
        )
        store.record_dispatch_failed(**common, error_class="TimeoutError")

    rows = load_news_memo_outcomes(store.path)
    assert len(rows) == 1
    assert rows[0]["dispatch_state"] == "dispatch_failed"
    assert rows[0]["accepted_at_utc"] == ""
    assert rows[0]["terminal_state"] == terminal_state
    assert rows[0]["reason"] == reason
    assert rows[0]["error_class"] == error_class
    assert rows[0]["task_id"] == "task-published-despite-client-error"
    assert rows[0]["completed_at_utc"]

    reconciliation = store.reconcile_latest([common["source_id"]])
    expected_classification = (
        "needs-retry" if terminal_state == "needs_retry" else terminal_state
    )
    assert reconciliation["counts"][expected_classification] == 1
    assert reconciliation["counts"]["dispatch-failed"] == 0


def test_news_memo_outcome_corruption_fails_closed_without_overwrite(
    tmp_path: Path,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    original = b'{"schema_version":1,"correlation_id":"truncated"\n'
    store.path.write_bytes(original)

    with pytest.raises(json.JSONDecodeError):
        store.record_terminal(
            correlation_id="new-attempt",
            source_id="news:new",
            attempt_started_at_utc="2026-07-19T09:00:00+00:00",
            task_id="task-new",
            terminal_state="completed",
        )

    assert store.path.read_bytes() == original
    reconciliation = store.reconcile_latest(["news:new"])
    assert reconciliation["status"] == "degraded"
    assert reconciliation["read_errors"] == 1
    assert reconciliation["read_error_classes"] == ["JSONDecodeError"]
    assert sum(reconciliation["counts"].values()) == 0


def test_news_memo_outcome_concurrent_process_writers_preserve_both_rows(
    tmp_path: Path,
) -> None:
    memos_path = tmp_path / "news_memos.jsonl"

    def write_outcome(correlation_id: str, source_id: str) -> None:
        store = NewsMemoOutcomeStore(memos_path=memos_path)
        store.record_terminal(
            correlation_id=correlation_id,
            source_id=source_id,
            attempt_started_at_utc="2026-07-19T10:00:00+00:00",
            task_id=f"task-{correlation_id}",
            terminal_state="completed",
        )

    context = multiprocessing.get_context("fork")
    first = context.Process(target=write_outcome, args=("concurrent-a", "news:a"))
    second = context.Process(target=write_outcome, args=("concurrent-b", "news:b"))
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert first.exitcode == 0
    assert second.exitcode == 0
    rows = [
        json.loads(line)
        for line in memos_path.with_name("news_memo_outcomes.jsonl")
        .read_text()
        .splitlines()
    ]
    assert [row["correlation_id"] for row in rows] == [
        "concurrent-a",
        "concurrent-b",
    ]


@pytest.mark.parametrize("first_writer", ["loader", "worker"])
def test_news_memo_outcome_files_preserve_shared_mode_in_either_writer_order(
    tmp_path: Path,
    first_writer: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memos_path = tmp_path / "news_memos.jsonl"
    loader_store = NewsMemoOutcomeStore(memos_path=memos_path)
    worker_store = NewsMemoOutcomeStore(memos_path=memos_path)
    common = {
        "correlation_id": f"shared-mode-{first_writer}",
        "source_id": f"news:shared-mode-{first_writer}",
        "attempt_started_at_utc": "2026-07-19T10:30:00+00:00",
        "task_id": f"task-shared-mode-{first_writer}",
    }
    parent_metadata = tmp_path.stat()
    ownership_updates: list[tuple[int, int]] = []

    monkeypatch.setattr(news_memo_outcomes.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        news_memo_outcomes.os,
        "fchown",
        lambda _descriptor, uid, gid: ownership_updates.append((uid, gid)),
    )

    previous_umask = os.umask(0o077)
    try:
        if first_writer == "loader":
            loader_store.record_dispatch_accepted(**common)
        else:
            worker_store.record_terminal(**common, terminal_state="completed")

        for shared_path in (loader_store.path, loader_store.lock_path):
            shared_metadata = shared_path.stat()
            assert stat.S_IMODE(shared_metadata.st_mode) == 0o660
            assert shared_metadata.st_uid == parent_metadata.st_uid
            assert shared_metadata.st_gid == parent_metadata.st_gid

        if first_writer == "loader":
            worker_store.record_terminal(**common, terminal_state="completed")
        else:
            loader_store.record_dispatch_accepted(**common)

        for shared_path in (loader_store.path, loader_store.lock_path):
            shared_metadata = shared_path.stat()
            assert stat.S_IMODE(shared_metadata.st_mode) == 0o660
            assert shared_metadata.st_uid == parent_metadata.st_uid
            assert shared_metadata.st_gid == parent_metadata.st_gid
    finally:
        os.umask(previous_umask)

    rows = load_news_memo_outcomes(loader_store.path)
    assert len(rows) == 1
    assert rows[0]["dispatch_state"] == "accepted"
    assert rows[0]["terminal_state"] == "completed"
    assert ownership_updates
    assert set(ownership_updates) == {(parent_metadata.st_uid, parent_metadata.st_gid)}


@pytest.mark.parametrize("first_writer", ["loader", "worker"])
def test_news_memo_outcome_lock_supports_shared_group_cross_uid_writer_order(
    tmp_path: Path,
    first_writer: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memos_path = tmp_path / "news_memos.jsonl"
    loader_store = NewsMemoOutcomeStore(memos_path=memos_path)
    worker_store = NewsMemoOutcomeStore(memos_path=memos_path)
    common = {
        "correlation_id": f"cross-uid-{first_writer}",
        "source_id": f"news:cross-uid-{first_writer}",
        "attempt_started_at_utc": "2026-07-19T10:35:00+00:00",
        "task_id": f"task-cross-uid-{first_writer}",
    }
    first_uid = 2001
    second_uid = 2002
    shared_gid = tmp_path.stat().st_gid
    current_uid = {"value": first_uid}
    lock_owner = {"value": None}
    lock_fchmod_attempts: list[int] = []
    real_fstat = os.fstat
    real_fchmod = os.fchmod

    def descriptor_name(file_descriptor: int) -> str:
        return Path(os.readlink(f"/proc/self/fd/{file_descriptor}")).name

    def simulated_fstat(file_descriptor: int) -> SimpleNamespace:
        metadata = real_fstat(file_descriptor)
        if descriptor_name(file_descriptor) == loader_store.lock_path.name:
            if lock_owner["value"] is None:
                lock_owner["value"] = current_uid["value"]
            simulated_uid = lock_owner["value"]
        else:
            simulated_uid = current_uid["value"]
        return SimpleNamespace(
            st_mode=metadata.st_mode,
            st_uid=simulated_uid,
            st_gid=shared_gid,
        )

    def owner_enforcing_fchmod(file_descriptor: int, mode: int) -> None:
        if descriptor_name(file_descriptor) == loader_store.lock_path.name:
            if lock_owner["value"] is None:
                lock_owner["value"] = current_uid["value"]
            lock_fchmod_attempts.append(current_uid["value"])
            if lock_owner["value"] != current_uid["value"]:
                raise PermissionError("simulated non-owner fchmod EPERM")
        real_fchmod(file_descriptor, mode)

    monkeypatch.setattr(news_memo_outcomes.os, "geteuid", lambda: current_uid["value"])
    monkeypatch.setattr(news_memo_outcomes.os, "fstat", simulated_fstat)
    monkeypatch.setattr(news_memo_outcomes.os, "fchmod", owner_enforcing_fchmod)
    monkeypatch.setattr(
        news_memo_outcomes,
        "_cooperative_owner",
        lambda _path: (first_uid, shared_gid),
    )

    if first_writer == "loader":
        loader_store.record_dispatch_accepted(**common)
    else:
        worker_store.record_terminal(**common, terminal_state="completed")

    current_uid["value"] = second_uid
    if first_writer == "loader":
        worker_store.record_terminal(**common, terminal_state="completed")
    else:
        loader_store.record_dispatch_accepted(**common)

    rows = load_news_memo_outcomes(loader_store.path)
    assert len(rows) == 1
    assert rows[0]["dispatch_state"] == "accepted"
    assert rows[0]["terminal_state"] == "completed"
    assert lock_fchmod_attempts == [first_uid]
    assert stat.S_IMODE(loader_store.lock_path.stat().st_mode) == 0o660


def test_news_memo_outcome_root_normalizes_existing_shared_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / "news_memo_outcomes.jsonl.lock"
    lock_path.touch(mode=0o660)
    lock_path.chmod(0o660)
    owner_uid = 2001
    owner_gid = lock_path.stat().st_gid
    ownership_updates: list[tuple[int, int]] = []
    mode_updates: list[int] = []

    monkeypatch.setattr(news_memo_outcomes.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        news_memo_outcomes.os,
        "fchown",
        lambda _descriptor, uid, gid: ownership_updates.append((uid, gid)),
    )
    monkeypatch.setattr(
        news_memo_outcomes.os,
        "fchmod",
        lambda _descriptor, mode: mode_updates.append(mode),
    )

    file_descriptor = os.open(lock_path, os.O_RDWR | os.O_CLOEXEC)
    try:
        news_memo_outcomes._apply_cooperative_metadata(
            file_descriptor,
            owner_uid=owner_uid,
            owner_gid=owner_gid,
            allow_existing_non_owner=True,
        )
    finally:
        os.close(file_descriptor)

    assert ownership_updates == [(owner_uid, owner_gid)]
    assert mode_updates == [0o660]


@pytest.mark.parametrize("unsafe_mode", [0o664, 0o666])
def test_news_memo_outcome_non_owner_rejects_unsafe_lock_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe_mode: int,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": "unsafe-cross-uid-lock",
        "source_id": "news:unsafe-cross-uid-lock",
        "attempt_started_at_utc": "2026-07-19T10:40:00+00:00",
        "task_id": "task-unsafe-cross-uid-lock",
    }
    store.record_dispatch_accepted(**common)
    original = store.path.read_bytes()
    store.lock_path.chmod(unsafe_mode)

    owner_uid = 2001
    writer_uid = 2002
    shared_gid = tmp_path.stat().st_gid
    real_fstat = os.fstat
    fchmod_attempts: list[int] = []

    def simulated_fstat(file_descriptor: int) -> SimpleNamespace:
        metadata = real_fstat(file_descriptor)
        target_name = Path(os.readlink(f"/proc/self/fd/{file_descriptor}")).name
        return SimpleNamespace(
            st_mode=metadata.st_mode,
            st_uid=owner_uid if target_name == store.lock_path.name else writer_uid,
            st_gid=shared_gid,
        )

    def forbidden_fchmod(file_descriptor: int, _mode: int) -> None:
        fchmod_attempts.append(file_descriptor)
        raise AssertionError("non-owner must not attempt to repair lock metadata")

    monkeypatch.setattr(news_memo_outcomes.os, "geteuid", lambda: writer_uid)
    monkeypatch.setattr(news_memo_outcomes.os, "fstat", simulated_fstat)
    monkeypatch.setattr(news_memo_outcomes.os, "fchmod", forbidden_fchmod)
    monkeypatch.setattr(
        news_memo_outcomes,
        "_cooperative_owner",
        lambda _path: (owner_uid, shared_gid),
    )

    with pytest.raises(PermissionError, match="unsafe cooperative lock metadata"):
        store.record_terminal(**common, terminal_state="completed")

    assert fchmod_attempts == []
    assert store.path.read_bytes() == original


@pytest.mark.parametrize(
    "invalid_timestamp",
    ["not-a-timestamp", "2026-07-19T10:45:00"],
)
def test_news_memo_outcome_writer_rejects_malformed_or_naive_attempt_timestamp(
    tmp_path: Path,
    invalid_timestamp: str,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")

    with pytest.raises(ValueError, match="attempt_started_at_utc"):
        store.record_terminal(
            correlation_id="invalid-timestamp",
            source_id="news:invalid-timestamp",
            attempt_started_at_utc=invalid_timestamp,
            task_id="task-invalid-timestamp",
            terminal_state="completed",
        )

    assert not store.path.exists()


@pytest.mark.parametrize(
    ("field_name", "invalid_timestamp"),
    [
        ("attempt_started_at_utc", "not-a-timestamp"),
        ("accepted_at_utc", "2026-07-19T10:45:00"),
        ("completed_at_utc", "not-a-timestamp"),
        ("updated_at_utc", "2026-07-19T10:45:00"),
    ],
)
def test_news_memo_outcome_reader_rejects_invalid_lifecycle_timestamps(
    tmp_path: Path,
    field_name: str,
    invalid_timestamp: str,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": "invalid-lifecycle",
        "source_id": "news:invalid-lifecycle",
        "attempt_started_at_utc": "2026-07-19T10:45:00+00:00",
        "task_id": "task-invalid-lifecycle",
    }
    store.record_dispatch_accepted(**common)
    store.record_terminal(**common, terminal_state="completed")
    row = load_news_memo_outcomes(store.path)[0]
    row[field_name] = invalid_timestamp
    store.path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=field_name):
        load_news_memo_outcomes(store.path)


def test_news_memo_outcome_canonicalizes_equivalent_offset_attempts(
    tmp_path: Path,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    store.record_terminal(
        correlation_id="equivalent-a",
        source_id="news:equivalent-offsets",
        attempt_started_at_utc="2026-07-19T20:00:00+10:00",
        task_id="task-equivalent-a",
        terminal_state="completed",
    )
    store.record_terminal(
        correlation_id="equivalent-z",
        source_id="news:equivalent-offsets",
        attempt_started_at_utc="2026-07-19T10:00:00Z",
        task_id="task-equivalent-z",
        terminal_state="failed",
        reason="worker_exception",
        error_class="RuntimeError",
    )

    rows = load_news_memo_outcomes(store.path)
    assert [row["attempt_started_at_utc"] for row in rows] == [
        "2026-07-19T10:00:00+00:00",
        "2026-07-19T10:00:00+00:00",
    ]
    reconciliation = store.reconcile_latest(["news:equivalent-offsets"])
    assert reconciliation["counts"]["failed"] == 1
    assert reconciliation["samples"]["failed"] == [
        {
            "source_id": "news:equivalent-offsets",
            "correlation_id": "equivalent-z",
            "task_id": "task-equivalent-z",
        }
    ]


def test_news_memo_outcome_reader_rejects_incomplete_schema(
    tmp_path: Path,
) -> None:
    outcomes_path = tmp_path / "news_memo_outcomes.jsonl"
    outcomes_path.write_text(
        json.dumps({"schema_version": 1, "correlation_id": "incomplete"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="schema fields"):
        load_news_memo_outcomes(outcomes_path)


@pytest.mark.parametrize("invalid_schema_version", [True, 1.0, "1"])
def test_news_memo_outcome_reader_rejects_non_integer_schema_version(
    tmp_path: Path,
    invalid_schema_version: object,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    store.record_dispatch_accepted(
        correlation_id="invalid-schema-version",
        source_id="news:invalid-schema-version",
        attempt_started_at_utc="2026-07-19T10:50:00+00:00",
        task_id="task-invalid-schema-version",
    )
    row = load_news_memo_outcomes(store.path)[0]
    row["schema_version"] = invalid_schema_version
    store.path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema_version"):
        load_news_memo_outcomes(store.path)


@pytest.mark.parametrize(
    "field_name",
    [
        "correlation_id",
        "source_id",
        "task_id",
        "attempt_started_at_utc",
        "dispatch_state",
        "accepted_at_utc",
        "terminal_state",
        "reason",
        "error_class",
        "completed_at_utc",
        "updated_at_utc",
    ],
)
def test_news_memo_outcome_reader_rejects_noncanonical_stored_strings(
    tmp_path: Path,
    field_name: str,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": "noncanonical-string",
        "source_id": "news:noncanonical-string",
        "attempt_started_at_utc": "2026-07-19T10:55:00+00:00",
        "task_id": "task-noncanonical-string",
    }
    store.record_dispatch_accepted(**common)
    store.record_terminal(
        **common,
        terminal_state="completed",
        reason="completed_reason",
        error_class="NoError",
    )
    row = load_news_memo_outcomes(store.path)[0]
    row[field_name] = f" {row[field_name]} "
    store.path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=rf"{field_name}.*non-canonical"):
        load_news_memo_outcomes(store.path)


def test_news_memo_outcome_noncanonical_identity_fails_closed_without_mutation(
    tmp_path: Path,
) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": "padded-identity",
        "source_id": "news:padded-identity",
        "attempt_started_at_utc": "2026-07-19T10:57:00+00:00",
        "task_id": "task-padded-identity",
    }
    store.record_dispatch_accepted(**common)
    row = load_news_memo_outcomes(store.path)[0]
    row["correlation_id"] = " padded-identity "
    original = (json.dumps(row) + "\n").encode()
    store.path.write_bytes(original)

    with pytest.raises(RuntimeError, match=r"correlation_id.*non-canonical"):
        store.record_terminal(**common, terminal_state="completed")

    assert store.path.read_bytes() == original
    reconciliation = store.reconcile_latest([common["source_id"]])
    assert reconciliation["status"] == "degraded"
    assert reconciliation["read_errors"] == 1
    assert reconciliation["read_error_classes"] == ["RuntimeError"]


def test_news_memo_outcome_conflicts_fail_closed(tmp_path: Path) -> None:
    store = NewsMemoOutcomeStore(memos_path=tmp_path / "news_memos.jsonl")
    common = {
        "correlation_id": "conflict-1",
        "source_id": "news:conflict",
        "attempt_started_at_utc": "2026-07-19T11:00:00+00:00",
        "task_id": "task-conflict",
    }
    store.record_dispatch_accepted(**common)

    for changed_field, changed_value, expected_error in (
        ("source_id", "news:different", "source_id conflict"),
        (
            "attempt_started_at_utc",
            "2026-07-19T11:01:00+00:00",
            "attempt_started_at_utc conflict",
        ),
        ("task_id", "task-different", "task_id conflict"),
    ):
        conflicting = {**common, changed_field: changed_value}
        before = store.path.read_bytes()
        with pytest.raises(RuntimeError, match=expected_error):
            store.record_dispatch_accepted(**conflicting)
        assert store.path.read_bytes() == before

    store.record_terminal(
        **common,
        terminal_state="needs_retry",
        reason="non_substantive_output",
    )
    before = store.path.read_bytes()
    with pytest.raises(RuntimeError, match="terminal_state conflict"):
        store.record_terminal(
            **common,
            terminal_state="failed",
            reason="worker_exception",
            error_class="RuntimeError",
        )
    assert store.path.read_bytes() == before
