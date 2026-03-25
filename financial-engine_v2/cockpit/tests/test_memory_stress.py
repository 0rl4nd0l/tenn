"""Stress tests for the memory system: large files, many writes, and compaction."""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from cockpit.core.agent.memory.store import MemoryStore
from cockpit.core.agent.memory.compaction import MemoryCompactor


# ---------------------------------------------------------------------------
# MemoryStore load tests
# ---------------------------------------------------------------------------


class TestMemoryStoreLoad:
    """MemoryStore under heavy write/read load."""

    @pytest.fixture
    def store(self, tmp_path):
        return MemoryStore(root=tmp_path)

    def test_many_session_turns(self, store):
        """Write 100 session turns and read them all back."""
        for i in range(100):
            store.append_session_turn("user", f"message {i}")
            store.append_session_turn("assistant", f"response {i}")

        turns = store.read_session_turns()
        assert len(turns) == 200
        assert turns[0]["content"] == "message 0"
        assert turns[199]["content"] == "response 99"

    def test_large_research_file(self, store):
        """Write a 50KB research file for a ticker, then read it back — verify integrity."""
        big_content = "Financial data: " + "x" * (50_000 - len("Financial data: "))
        assert len(big_content) == 50_000
        store.write_research("BHP", big_content)
        content = store.read_research("BHP")
        assert content == big_content, "Read-back content does not match written content"
        assert len(content) == 50_000

    def test_many_tickers(self, store):
        """Write research for 50 tickers and list them all."""
        for i in range(50):
            store.write_research(f"T{i:02d}", f"Data for ticker T{i:02d}")

        tickers = store.list_research_tickers()
        assert len(tickers) == 50
        assert "T00" in tickers
        assert "T49" in tickers

    def test_append_research_many_times(self, store):
        """Append to the same ticker 50 times and verify all content is present."""
        for i in range(50):
            store.append_research("BHP", f"Finding #{i}: metric value {i * 100}")

        content = store.read_research("BHP")
        assert "Finding #0" in content
        assert "Finding #49" in content

    def test_rotate_session_multiple_times(self, store):
        """Rotate session 5 times, verify each archived file exists."""
        archived_paths = []
        for _ in range(5):
            store.append_session_turn("user", "turn")
            path = store.rotate_session()
            archived_paths.append(path)
            # Give each rotation a unique timestamp slot within the same hour:
            # The archive path uses hour granularity so multiple within the
            # same hour append to the same file — just verify file exists.

        for p in archived_paths:
            assert p.exists()

    def test_concurrent_session_writes(self, store):
        """Write 100 session turns rapidly (sequentially) and verify all are persisted in order."""
        for i in range(100):
            store.append_session_turn("user", f"turn-{i}")

        turns = store.read_session_turns()
        assert len(turns) == 100
        for i, turn in enumerate(turns):
            assert turn["content"] == f"turn-{i}", (
                f"Turn {i} out of order: got {turn['content']!r}"
            )

    def test_concurrent_session_writes_threaded(self, store):
        """Concurrent writes from multiple threads complete without errors."""
        errors = []

        def writer(start_idx):
            try:
                for i in range(20):
                    store.append_session_turn("user", f"msg-{start_idx}-{i}")
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent writes: {errors}"
        turns = store.read_session_turns()
        assert len(turns) == 100  # 5 threads × 20 turns

    def test_write_then_overwrite_research(self, store):
        """write_research overwrites — not appends — on second call."""
        store.write_research("CSL", "original content")
        store.write_research("CSL", "replacement content")
        content = store.read_research("CSL")
        assert "replacement content" in content
        assert "original content" not in content

    def test_read_nonexistent_research_is_empty(self, store):
        """Reading research for a ticker that has no file returns empty string."""
        assert store.read_research("NOPE") == ""

    def test_durable_round_trip(self, store):
        """Write and read durable memory."""
        store.write_durable("User prefers concise summaries.")
        assert "concise" in store.read_durable()

    def test_durable_append_accumulates(self, store):
        """Multiple durable appends accumulate without overwriting."""
        store.write_durable("Section A.")
        store.append_durable("Section B.")
        store.append_durable("Section C.")
        content = store.read_durable()
        assert "Section A." in content
        assert "Section B." in content
        assert "Section C." in content

    def test_session_turn_has_timestamp(self, store):
        """Each session turn includes a 'ts' ISO timestamp field."""
        store.append_session_turn("user", "hello")
        turns = store.read_session_turns()
        assert "ts" in turns[0]
        assert "T" in turns[0]["ts"]  # ISO format contains 'T' separator

    def test_empty_session_returns_empty_list(self, store):
        """read_session_turns on a fresh store returns []."""
        assert store.read_session_turns() == []

    def test_write_daily_and_read_back(self, store):
        """write_daily / read_daily round-trip."""
        store.write_daily("Today's summary.", date="2026-03-25")
        content = store.read_daily(date="2026-03-25")
        assert "Today's summary." in content

    def test_session_cleared_after_rotate(self, store):
        """After rotate_session, read_session_turns returns empty."""
        store.append_session_turn("user", "hi")
        store.rotate_session()
        assert store.read_session_turns() == []

    def test_session_rotation_under_load(self, store):
        """Write 200 turns, rotate, verify archive exists and current is empty, then write more."""
        for i in range(200):
            store.append_session_turn("user", f"pre-rotate turn {i}")

        assert len(store.read_session_turns()) == 200

        archive_path = store.rotate_session()

        # Archive must exist and contain data
        assert archive_path.exists(), "Archive file was not created"
        archive_content = archive_path.read_text(encoding="utf-8")
        assert "pre-rotate turn 0" in archive_content
        assert "pre-rotate turn 199" in archive_content

        # Current session must be empty after rotation
        assert store.read_session_turns() == []

        # Writing more turns to the fresh session must work normally
        for i in range(10):
            store.append_session_turn("assistant", f"post-rotate turn {i}")

        post_turns = store.read_session_turns()
        assert len(post_turns) == 10
        assert post_turns[0]["content"] == "post-rotate turn 0"

    def test_durable_memory_append(self, store):
        """Append to MEMORY.md 20 times, verify all entries present."""
        for i in range(20):
            store.append_durable(f"Entry {i}: important finding number {i}")

        content = store.read_durable()
        for i in range(20):
            assert f"Entry {i}: important finding number {i}" in content, (
                f"Entry {i} missing from durable memory"
            )


# ---------------------------------------------------------------------------
# MemoryCompactor tests
# ---------------------------------------------------------------------------


class TestCompaction:
    """MemoryCompactor under load."""

    @pytest.fixture
    def store(self, tmp_path):
        return MemoryStore(root=tmp_path)

    def test_compaction_triggers_at_threshold(self, store):
        """MemoryCompactor with a mock summarizer: >40 turns triggers compaction and calls summarizer."""
        for i in range(50):
            store.append_session_turn("user", f"message {i} with some padding content here")

        summarizer_calls = []

        def mock_summarizer(turns):
            summarizer_calls.append(len(turns))
            return f"Summarized {len(turns)} turns."

        compactor = MemoryCompactor(store, summarize_fn=mock_summarizer)
        result = compactor.maybe_compact()

        assert result is True, "maybe_compact() should return True when compaction fires"
        assert len(summarizer_calls) == 1, "summarizer must be called exactly once"
        assert summarizer_calls[0] > 0, "summarizer must receive at least one turn"
        # After compaction the session is shorter
        turns = store.read_session_turns()
        assert len(turns) < 50

    def test_compaction_does_not_trigger_under_threshold(self, store):
        """No compaction when turn count is well under the limit."""
        for i in range(10):
            store.append_session_turn("user", f"msg {i}")

        compactor = MemoryCompactor(store)
        assert compactor.maybe_compact() is False

    def test_compaction_with_summarizer(self, store):
        """Compaction passes old turns to the summarize_fn when provided."""
        for i in range(50):
            store.append_session_turn("user", f"detailed message {i} about BHP mining operations")

        called_with = []

        def fake_summarize(turns):
            called_with.append(turns)
            return "Summary: discussed BHP mining operations."

        compactor = MemoryCompactor(store, summarize_fn=fake_summarize)
        compactor.maybe_compact()

        assert len(called_with) == 1
        # summarize_fn receives a list of turn dicts
        assert isinstance(called_with[0], list)
        assert all(isinstance(t, dict) for t in called_with[0])

    def test_compaction_writes_daily_log(self, store):
        """After compaction, a daily log entry exists."""
        for i in range(50):
            store.append_session_turn("user", f"msg {i}")

        compactor = MemoryCompactor(store, summarize_fn=lambda turns: "Daily summary.")
        compactor.maybe_compact()

        daily_dir = store.root / "daily"
        daily_files = list(daily_dir.glob("*.md"))
        assert len(daily_files) >= 1

    def test_compaction_keeps_recent_turns(self, store):
        """After compaction, the most recent turns survive in the active session."""
        messages = [f"unique-msg-{i}" for i in range(60)]
        for msg in messages:
            store.append_session_turn("user", msg)

        compactor = MemoryCompactor(store)
        compactor.maybe_compact()

        turns = store.read_session_turns()
        # The last messages should be in the kept half
        surviving_contents = [t["content"] for t in turns]
        assert "unique-msg-59" in surviving_contents

    def test_compaction_without_summarizer_drops_old_turns(self, store):
        """Without a summarize_fn, older turns are replaced by a placeholder."""
        for i in range(50):
            store.append_session_turn("user", f"msg {i}")

        compactor = MemoryCompactor(store, summarize_fn=None)
        result = compactor.maybe_compact()

        assert result is True
        # Check the daily file contains the placeholder
        daily_dir = store.root / "daily"
        daily_files = list(daily_dir.glob("*.md"))
        assert len(daily_files) >= 1
        content = daily_files[0].read_text()
        assert "[older turns dropped during compaction]" in content

    def test_custom_max_turns_threshold(self, store):
        """Custom max_turns triggers compaction at the specified count."""
        for i in range(15):
            store.append_session_turn("user", f"msg {i}")

        # Default (40) would not trigger; custom (10) should
        compactor = MemoryCompactor(store, max_turns=10)
        assert compactor.maybe_compact() is True

    def test_compaction_chars_threshold(self, store):
        """Compaction triggers when total char count exceeds max_chars."""
        # Each turn is about 500 chars; 50 turns = ~25 000 chars > default 24 000
        for i in range(50):
            store.append_session_turn("user", "x" * 500)

        compactor = MemoryCompactor(store, max_turns=10000, max_chars=24_000)
        assert compactor.maybe_compact() is True

    def test_double_compaction_reduces_further(self, store):
        """Running compaction twice reduces turn count again."""
        for i in range(80):
            store.append_session_turn("user", f"msg {i}")

        compactor = MemoryCompactor(store, max_turns=40)
        compactor.maybe_compact()
        count_after_first = len(store.read_session_turns())

        # Add more turns to push over threshold again
        for i in range(80, 120):
            store.append_session_turn("user", f"msg {i}")

        compactor.maybe_compact()
        count_after_second = len(store.read_session_turns())

        assert count_after_second <= count_after_first + 40


# ---------------------------------------------------------------------------
# MemorySearch load tests
# ---------------------------------------------------------------------------


class TestMemorySearchLoad:
    """MemorySearch with many documents (using a stub embedder)."""

    @staticmethod
    def _stub_embed(text: str) -> list[float]:
        """Deterministic 4-dimensional stub embedding."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        return [int(h[i : i + 2], 16) / 255.0 for i in range(0, 8, 2)]

    def test_sqlite_vec_many_documents(self, tmp_path):
        """Index 100 documents into MemorySearch, query, verify results returned (or graceful degradation)."""
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        if not search._available:
            # Graceful degradation: index and query must be no-ops, not exceptions
            search.index("text", source="research/T000")
            results = search.query("topic", top_k=5)
            assert results == []
            return

        for i in range(100):
            search.index(f"Document {i} about topic {i % 10}", source=f"research/T{i:03d}")

        results = search.query("topic 5", top_k=10)
        assert isinstance(results, list)
        assert len(results) <= 10
        # At least some results should be returned from a 100-doc index
        assert len(results) > 0

    def test_index_many_documents(self, tmp_path):
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        if not search._available:
            pytest.skip("sqlite-vec not available in this environment")

        for i in range(100):
            search.index(f"Document {i} about topic {i % 10}", source=f"research/T{i:03d}")

        results = search.query("topic 5", top_k=10)
        assert isinstance(results, list)
        assert len(results) <= 10

    def test_reindex_does_not_duplicate(self, tmp_path):
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        if not search._available:
            pytest.skip("sqlite-vec not available in this environment")

        search.index("original content", source="research/BHP")
        search.reindex_source("research/BHP", "updated content about BHP revenue")

        results = search.query("BHP", top_k=10)
        bhp_results = [r for r in results if r["source"] == "research/BHP"]
        assert len(bhp_results) <= 1

    def test_query_returns_correct_keys(self, tmp_path):
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        if not search._available:
            pytest.skip("sqlite-vec not available in this environment")

        search.index("BHP revenue is $55B", source="research/BHP")
        results = search.query("revenue", top_k=1)

        if results:
            assert "source" in results[0]
            assert "content" in results[0]
            assert "score" in results[0]

    def test_empty_index_returns_empty_list(self, tmp_path):
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        if not search._available:
            pytest.skip("sqlite-vec not available in this environment")

        results = search.query("anything", top_k=5)
        assert results == []

    def test_search_unavailable_graceful_degradation(self, tmp_path):
        """When sqlite-vec is unavailable, index/query are no-ops (no crash)."""
        from cockpit.core.agent.memory.search import MemorySearch

        search = MemorySearch(
            db_path=tmp_path / "test.db",
            embed_fn=self._stub_embed,
            dims=4,
        )
        # Force unavailable
        search._available = False
        search.index("text", source="research/BHP")  # should not raise
        results = search.query("text", top_k=5)
        assert results == []
