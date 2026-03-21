import json
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

import scripts.run_news_pipeline as RUN


class RunNewsPipelineTests(unittest.TestCase):
    def _run_main(self, argv):
        """Run main() and capture stdout, return (rc, parsed_json_output)."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            rc = RUN.main(argv)
        output = buf.getvalue()
        # Find the first top-level JSON object (starts at column 0)
        first_brace = output.find("{")
        payload = json.loads(output[first_brace:]) if first_brace >= 0 else {}
        return rc, payload

    @patch("scripts.run_news_pipeline.write_run_reports", return_value={})
    @patch("scripts.run_news_pipeline.run_provider_daily", return_value=("test-run-id", []))
    @patch("scripts.run_news_pipeline.build_provider", return_value=MagicMock())
    @patch("scripts.run_news_pipeline.EntityLinker")
    @patch("scripts.run_news_pipeline.NewsArticleStore")
    @patch("scripts.run_news_pipeline.load_tickers", return_value=["CBA.AX", "BHP.AX"])
    def test_main_returns_zero_with_providers_and_runs(
        self, mock_lt, mock_store, mock_linker, mock_bp, mock_rpd, mock_wrr
    ):
        """main() succeeds and emits payload with 'providers' and 'runs' keys."""
        rc, payload = self._run_main(["--skip-gdelt-doc-api"])
        self.assertEqual(rc, 0)
        self.assertIn("providers", payload)
        self.assertIn("runs", payload)

    @patch("scripts.run_news_pipeline.write_run_reports", return_value={})
    @patch("scripts.run_news_pipeline.run_provider_daily", return_value=("test-run-id", []))
    @patch("scripts.run_news_pipeline.build_provider", return_value=MagicMock())
    @patch("scripts.run_news_pipeline.EntityLinker")
    @patch("scripts.run_news_pipeline.NewsArticleStore")
    @patch("scripts.run_news_pipeline.load_tickers", return_value=["CBA.AX", "BHP.AX"])
    def test_main_skip_gdelt_doc_api_flag(
        self, mock_lt, mock_store, mock_linker, mock_bp, mock_rpd, mock_wrr
    ):
        """--skip-gdelt-doc-api flag is accepted and reflected in output."""
        rc, payload = self._run_main(["--skip-gdelt-doc-api"])
        self.assertEqual(rc, 0)
        self.assertTrue(payload.get("skip_gdelt_doc_api"))


if __name__ == "__main__":
    unittest.main()
