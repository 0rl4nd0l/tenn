import contextlib
import importlib.util
import io
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.source_registry import SourceRegistry, utc_now_iso
from app.services.transcript_watcher import (
    DEFAULT_POLL_INTERVAL_SECONDS,
    TranscriptMetadata,
    TranscriptProcessor,
    TranscriptWatcher,
    compute_transcript_source_id,
    render_transcript_drop_file,
)
from app.services.youtube_transcript_fetcher import (
    TranscriptUnavailableError,
    YoutubeTranscriptFetcher,
    YoutubeVideo,
)


def _load_transcript_daemon_module():
    module_path = ROOT / "scripts" / "run_transcript_daemon.py"
    spec = importlib.util.spec_from_file_location("run_transcript_daemon", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTranscriptWatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self._testMethodName)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.inbox = self.tmp / "inbox" / "transcripts"
        self.books = self.tmp / "inbox" / "books"
        self.processed = self.tmp / "processed"
        self.failed = self.tmp / "failed"
        self.state_path = self.tmp / "processed" / ".transcript_watcher_state.json"
        self.registry_path = self.tmp / "research_memory" / "source_registry.jsonl"
        self.channel_registry_path = self.tmp / "channel_registry.json"

    def tearDown(self) -> None:
        if self.tmp.exists():
            for path in sorted(self.tmp.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

    def _processor(self, runner):
        return TranscriptProcessor(
            inbox_dir=self.inbox,
            books_dir=self.books,
            processed_dir=self.processed,
            failed_dir=self.failed,
            state_path=self.state_path,
            registry_path=self.registry_path,
            ingest_runner=runner,
        )

    def _write_drop(
        self,
        name: str,
        *,
        text: str,
        metadata: TranscriptMetadata,
    ) -> Path:
        self.inbox.mkdir(parents=True, exist_ok=True)
        path = self.inbox / name
        path.write_text(render_transcript_drop_file(transcript_text=text, metadata=metadata), encoding="utf-8")
        return path

    def test_processor_ingests_new_file_and_moves_to_processed(self) -> None:
        captured = {}

        def fake_runner(job):
            captured["path"] = job.path
            captured["metadata"] = job.metadata
            captured["text"] = job.transcript_text
            return {"ok": True, "source_id": "youtube_transcript:test"}

        processor = self._processor(fake_runner)
        metadata = TranscriptMetadata(
            source_name="Alpha Channel Interview",
            source_type="youtube_transcript",
            speaker="Alpha Channel",
            published_at="2026-03-01T00:00:00Z",
            topic_tags=("alpha", "moat"),
            credibility_weight=0.55,
            decay_half_life_days=14.0,
        )
        drop = self._write_drop(
            "alpha.txt",
            text="00:00 Demand is improving.\n00:15 Margin expansion is the catalyst.",
            metadata=metadata,
        )

        result = processor.process_file(drop)

        self.assertEqual(result.status, "ingested")
        self.assertEqual(result.source_id, "youtube_transcript:test")
        self.assertEqual(captured["metadata"].source_name, "Alpha Channel Interview")
        self.assertEqual(captured["metadata"].topic_tags, ("alpha", "moat"))
        self.assertIn("Demand is improving.", captured["text"])
        self.assertTrue((self.processed / "alpha.txt").exists())
        self.assertFalse(drop.exists())

    def test_processor_ingests_plain_txt_file_with_filename_defaults(self) -> None:
        captured = {}

        def fake_runner(job):
            captured["metadata"] = job.metadata
            captured["text"] = job.transcript_text
            return {"ok": True, "source_id": "youtube_transcript:plain"}

        processor = self._processor(fake_runner)
        self.inbox.mkdir(parents=True, exist_ok=True)
        drop = self.inbox / "alpha.txt"
        drop.write_text(
            "00:00 Demand is improving.\n00:15 Margin expansion is the catalyst.",
            encoding="utf-8",
        )
        expected_published_at = "2026-03-06T00:00:00Z"
        timestamp = int(datetime(2026, 3, 6, tzinfo=timezone.utc).timestamp())
        os.utime(drop, (timestamp, timestamp))

        result = processor.process_file(drop)

        self.assertEqual(result.status, "ingested")
        self.assertEqual(captured["metadata"].source_name, "alpha.txt")
        self.assertEqual(captured["metadata"].source_type, "youtube_transcript")
        self.assertEqual(captured["metadata"].speaker, "alpha")
        self.assertEqual(captured["metadata"].published_at, expected_published_at)
        self.assertIn("Demand is improving.", captured["text"])
        self.assertTrue((self.processed / "alpha.txt").exists())

    def test_processor_skips_duplicate_transcript_from_source_registry(self) -> None:
        calls = []

        def fake_runner(job):
            calls.append(job)
            return {"ok": True, "source_id": "should-not-run"}

        processor = self._processor(fake_runner)
        metadata = TranscriptMetadata(
            source_name="Duplicate Interview",
            source_type="youtube_transcript",
            speaker="Macro Mike",
            published_at="2026-03-02T00:00:00Z",
            topic_tags=("macro",),
            credibility_weight=0.55,
            decay_half_life_days=14.0,
        )
        transcript_text = "00:00 Rates may fall.\n00:10 Demand should recover."
        source_id = compute_transcript_source_id(
            transcript_text=transcript_text,
            metadata=metadata,
        )
        registry = SourceRegistry(self.registry_path)
        registry.upsert(
            {
                "source_id": source_id,
                "source_type": metadata.source_type,
                "source_name": metadata.source_name,
                "credibility_weight": metadata.credibility_weight,
                "time_decay_half_life_days": metadata.decay_half_life_days,
                "review_status": "pending",
                "ingested_at": utc_now_iso(),
            }
        )
        drop = self._write_drop("duplicate.txt", text=transcript_text, metadata=metadata)

        result = processor.process_file(drop)

        self.assertEqual(result.status, "duplicate")
        self.assertEqual(result.source_id, source_id)
        self.assertEqual(calls, [])
        self.assertTrue((self.processed / "duplicate.txt").exists())

    def test_processor_skips_duplicate_filename_using_state_file(self) -> None:
        calls = []

        def fake_runner(job):
            calls.append(job.transcript_text)
            return {"ok": True, "source_id": f"youtube_transcript:repeat:{len(calls)}"}

        processor = self._processor(fake_runner)
        self.inbox.mkdir(parents=True, exist_ok=True)

        first_drop = self.inbox / "repeat.txt"
        first_drop.write_text("00:00 First transcript body.", encoding="utf-8")

        first_result = processor.process_file(first_drop)

        second_drop = self.inbox / "repeat.txt"
        second_drop.write_text("00:00 Second transcript body.", encoding="utf-8")

        second_result = processor.process_file(second_drop)

        self.assertEqual(first_result.status, "ingested")
        self.assertEqual(second_result.status, "duplicate")
        self.assertEqual(calls, ["00:00 First transcript body."])
        self.assertTrue(self.state_path.exists())
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["processed_filenames"], ["repeat.txt"])
        processed_files = sorted(path.name for path in self.processed.glob("repeat*.txt"))
        self.assertEqual(processed_files, ["repeat.txt", "repeat_1.txt"])

    def test_processor_moves_failed_file_to_failed_folder(self) -> None:
        def fake_runner(job):
            raise RuntimeError("ingest failed")

        processor = self._processor(fake_runner)
        metadata = TranscriptMetadata(
            source_name="Broken File",
            source_type="market_commentary",
            speaker="Broken File",
            published_at="2026-03-03T00:00:00Z",
        )
        drop = self._write_drop("broken.txt", text="Transcript body", metadata=metadata)

        result = processor.process_file(drop)

        self.assertEqual(result.status, "failed")
        self.assertIn("ingest failed", result.error)
        self.assertTrue((self.failed / "broken.txt").exists())

    def test_watcher_polls_txt_files_only(self) -> None:
        seen = []

        def fake_runner(job):
            seen.append(job.path.name)
            return {"ok": True, "source_id": f"market_commentary:{job.path.stem}"}

        processor = self._processor(fake_runner)
        metadata = TranscriptMetadata(
            source_name="Watcher File",
            source_type="market_commentary",
            speaker="Watcher File",
            published_at="2026-03-04T00:00:00Z",
        )
        self._write_drop("watch-me.txt", text="Transcript body", metadata=metadata)
        self.inbox.mkdir(parents=True, exist_ok=True)
        (self.inbox / "ignore.md").write_text("not a transcript", encoding="utf-8")
        watcher = TranscriptWatcher(processor=processor, poll_interval_seconds=10.0)

        results = watcher.poll_once()

        self.assertEqual([result.status for result in results], ["ingested"])
        self.assertEqual(seen, ["watch-me.txt"])
        self.assertTrue((self.inbox / "ignore.md").exists())

    def test_watcher_default_poll_interval_is_five_seconds(self) -> None:
        watcher = TranscriptWatcher(processor=self._processor(lambda job: {"ok": True}))
        self.assertEqual(DEFAULT_POLL_INTERVAL_SECONDS, 5.0)
        self.assertEqual(watcher.poll_interval_seconds, 5.0)

    def test_youtube_fetcher_ingests_enabled_channel_transcripts_only(self) -> None:
        ingested = []

        def fake_runner(job):
            ingested.append(job.metadata)
            return {"ok": True, "source_id": f"youtube_transcript:{job.path.stem}"}

        processor = self._processor(fake_runner)
        self.channel_registry_path.write_text(
            json.dumps(
                {
                    "channels": [
                        {
                            "name": "Enabled Channel",
                            "channel_id": "UC_ENABLED",
                            "credibility_weight": 0.61,
                            "enabled": True,
                        },
                        {
                            "name": "Disabled Channel",
                            "channel_id": "UC_DISABLED",
                            "credibility_weight": 0.2,
                            "enabled": False,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        listed_channels = []

        def fake_list(channel, limit):
            listed_channels.append((channel.channel_id, limit))
            return [
                YoutubeVideo(
                    video_id="vid-1",
                    title="Enabled Channel March Update",
                    channel_name=channel.name,
                    published_at="2026-03-05T00:00:00Z",
                    webpage_url="https://example.com/vid-1",
                ),
                YoutubeVideo(
                    video_id="vid-2",
                    title="No Transcript",
                    channel_name=channel.name,
                    published_at="2026-03-05T01:00:00Z",
                    webpage_url="https://example.com/vid-2",
                ),
            ]

        def fake_fetch(video):
            if video.video_id == "vid-2":
                raise TranscriptUnavailableError("transcript unavailable")
            return "00:00 Fresh transcript.\n00:12 Commentary continues."

        fetcher = YoutubeTranscriptFetcher(
            channel_registry_path=self.channel_registry_path,
            processor=processor,
            list_videos_fn=fake_list,
            fetch_transcript_fn=fake_fetch,
            video_limit=5,
        )

        results = fetcher.poll_once()

        self.assertEqual(listed_channels, [("UC_ENABLED", 5)])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "ingested")
        self.assertEqual(ingested[0].speaker, "Enabled Channel")
        self.assertEqual(ingested[0].credibility_weight, 0.61)
        processed_files = sorted(path.name for path in self.processed.glob("*.txt"))
        self.assertEqual(processed_files, ["enabled-channel-march-update_vid-1.txt"])

    def test_youtube_fetcher_skips_already_ingested_video_without_writing_duplicate_file(self) -> None:
        def fake_runner(job):
            return {"ok": True, "source_id": "should-not-run"}

        processor = self._processor(fake_runner)
        self.channel_registry_path.write_text(
            json.dumps(
                {
                    "channels": [
                        {
                            "name": "Enabled Channel",
                            "channel_id": "UC_ENABLED",
                            "credibility_weight": 0.61,
                            "enabled": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        transcript_text = "00:00 Fresh transcript.\n00:12 Commentary continues."
        metadata = TranscriptMetadata(
            source_name="Enabled Channel March Update",
            source_type="youtube_transcript",
            speaker="Enabled Channel",
            published_at="2026-03-05T00:00:00Z",
            credibility_weight=0.61,
            decay_half_life_days=14.0,
        )
        source_id = compute_transcript_source_id(
            transcript_text=transcript_text,
            metadata=metadata,
        )
        registry = SourceRegistry(self.registry_path)
        registry.upsert(
            {
                "source_id": source_id,
                "source_type": metadata.source_type,
                "source_name": metadata.source_name,
                "credibility_weight": metadata.credibility_weight,
                "time_decay_half_life_days": metadata.decay_half_life_days,
                "review_status": "pending",
                "ingested_at": utc_now_iso(),
            }
        )

        def fake_list(channel, limit):
            return [
                YoutubeVideo(
                    video_id="vid-1",
                    title="Enabled Channel March Update",
                    channel_name=channel.name,
                    published_at="2026-03-05T00:00:00Z",
                    webpage_url="https://example.com/vid-1",
                )
            ]

        def fake_fetch(video):
            return transcript_text

        fetcher = YoutubeTranscriptFetcher(
            channel_registry_path=self.channel_registry_path,
            processor=processor,
            list_videos_fn=fake_list,
            fetch_transcript_fn=fake_fetch,
            video_limit=5,
        )

        results = fetcher.poll_once()

        self.assertEqual(results, [])
        self.assertEqual(list(self.processed.glob("*.txt")), [])

    def test_transcript_daemon_youtube_poll_failure_is_non_fatal(self) -> None:
        module = _load_transcript_daemon_module()

        class FailingFetcher:
            def maybe_poll(self):
                raise RuntimeError("network down")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            results = module._poll_youtube_once(FailingFetcher())

        self.assertEqual(results, [])
        self.assertIn("[youtube] poll failed: network down", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
