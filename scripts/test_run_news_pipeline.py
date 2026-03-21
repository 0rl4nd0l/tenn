import json
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.run_news_pipeline as RUN


class RunNewsPipelineTests(unittest.TestCase):
    def _run_main(self, argv):
        """Run main() and capture stdout, return (rc, parsed_json_output)."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            rc = RUN.main(argv)
        output = buf.getvalue()
        first_brace = output.find("{")
        payload = json.loads(output[first_brace:]) if first_brace >= 0 else {}
        return rc, payload

    @patch("scripts.run_news_pipeline.write_run_reports", return_value={})
    @patch("scripts.run_news_pipeline.run_provider_daily", return_value=("test-run-id", []))
    @patch("scripts.run_news_pipeline.build_provider", return_value=MagicMock())
    @patch("scripts.run_news_pipeline.EntityLinker")
    @patch("scripts.run_news_pipeline.NewsArticleStore")
    @patch("scripts.run_news_pipeline.load_tickers", return_value=["CBA.AX", "BHP.AX"])
    def test_main_runs_providers_with_skip_flag(
        self, mock_lt, mock_store, mock_linker, mock_bp, mock_rpd, mock_wrr
    ):
        """The provider loop still runs when the optional GDELT-doc step is skipped."""
        rc, payload = self._run_main(["--skip-gdelt-doc-api"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["providers"], ["eodhd", "gdelt"])
        self.assertEqual(payload["skip_gdelt_doc_api"], True)
        self.assertEqual(payload["mode"], "daily")
        self.assertEqual(len(payload["runs"]), 2)
        self.assertEqual(mock_bp.call_count, 2)
        self.assertEqual(mock_rpd.call_count, 2)
        self.assertEqual(
            [call.kwargs["provider_name"] for call in mock_bp.call_args_list],
            ["eodhd", "gdelt"],
        )
        self.assertTrue(all(call.kwargs["provider"] is mock_bp.return_value for call in mock_rpd.call_args_list))
        mock_rpd.assert_any_call(
            store=mock_store.return_value,
            linker=mock_linker.return_value,
            provider=mock_bp.return_value,
            lane="high_precision",
            tickers=["CBA.AX", "BHP.AX"],
            since_hours=36,
            run_id="",
        )
        mock_wrr.assert_called()

    @patch("scripts.run_news_pipeline.write_run_reports", return_value={})
    @patch("scripts.run_news_pipeline.run_provider_daily", return_value=("test-run-id", []))
    @patch("scripts.run_news_pipeline.build_provider", return_value=MagicMock())
    @patch("scripts.run_news_pipeline.EntityLinker")
    @patch("scripts.run_news_pipeline.NewsArticleStore")
    @patch("scripts.run_news_pipeline.load_tickers", return_value=["CBA.AX", "BHP.AX"])
    @patch("scripts.run_news_pipeline._run_gdelt_doc_api", return_value=True)
    def test_main_runs_gdelt_doc_by_default(
        self, mock_gdelt_doc, mock_lt, mock_store, mock_linker, mock_bp, mock_rpd, mock_wrr
    ):
        """The optional GDELT-doc step runs when the skip flag is absent."""
        rc, payload = self._run_main([])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["providers"], ["eodhd", "gdelt"])
        self.assertEqual(payload["skip_gdelt_doc_api"], False)
        self.assertEqual(len(payload["runs"]), 2)
        self.assertEqual(mock_bp.call_count, 2)
        self.assertEqual(mock_rpd.call_count, 2)
        self.assertEqual(mock_gdelt_doc.call_count, 1)
        mock_gdelt_doc.assert_called_once()
        self.assertEqual(
            [call.kwargs["provider_name"] for call in mock_bp.call_args_list],
            ["eodhd", "gdelt"],
        )
        self.assertTrue(all(call.kwargs["provider"] is mock_bp.return_value for call in mock_rpd.call_args_list))

    @patch("scripts.run_news_pipeline.write_run_reports", return_value={})
    @patch("scripts.run_news_pipeline.run_provider_daily", return_value=("test-run-id", []))
    @patch("scripts.run_news_pipeline.build_provider", return_value=MagicMock())
    @patch("scripts.run_news_pipeline.EntityLinker")
    @patch("scripts.run_news_pipeline.NewsArticleStore")
    @patch("scripts.run_news_pipeline.load_tickers", return_value=["CBA.AX", "BHP.AX"])
    @patch("scripts.run_news_pipeline._run_gdelt_doc_api", return_value=True)
    def test_main_skip_gdelt_doc_api_flag(
        self, mock_gdelt_doc, mock_lt, mock_store, mock_linker, mock_bp, mock_rpd, mock_wrr
    ):
        """--skip-gdelt-doc-api suppresses the optional GDELT-doc step and still runs providers."""
        rc, payload = self._run_main(["--skip-gdelt-doc-api"])
        self.assertEqual(rc, 0)
        self.assertEqual(payload["providers"], ["eodhd", "gdelt"])
        self.assertEqual(payload["skip_gdelt_doc_api"], True)
        self.assertEqual(len(payload["runs"]), 2)
        self.assertEqual(mock_bp.call_count, 2)
        self.assertEqual(mock_rpd.call_count, 2)
        mock_gdelt_doc.assert_not_called()
        self.assertEqual(
            [call.kwargs["provider_name"] for call in mock_bp.call_args_list],
            ["eodhd", "gdelt"],
        )
        self.assertTrue(all(call.kwargs["provider"] is mock_bp.return_value for call in mock_rpd.call_args_list))


if __name__ == "__main__":
    unittest.main()
