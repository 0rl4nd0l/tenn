#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chart_args import prepare_chart_action_args  # noqa: E402


class _ActionRegistryStub:
    @staticmethod
    def parse_kv_args(raw: str) -> dict:
        out: dict = {}
        for token in str(raw or "").split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if key == "limit":
                try:
                    out[key] = int(value)
                except Exception:
                    out[key] = value
            else:
                out[key] = value
        return out


class _ToolRouterRows:
    def build_candlestick_ohlc_lines(
        self,
        ticker: str,
        *,
        range_: str = "1y",
        interval: str = "1d",
        max_history_rows: int = 260,
    ) -> list[dict]:  # noqa: ARG002
        return [
            {
                "timestamp": "2026-03-01T00:00:00+00:00",
                "open": 40.1,
                "high": 40.9,
                "low": 39.8,
                "close": 40.5,
                "volume": 123,
            }
        ]


class _ToolRouterEmpty:
    def build_candlestick_ohlc_lines(
        self,
        ticker: str,
        *,
        range_: str = "1y",
        interval: str = "1d",
        max_history_rows: int = 260,
    ) -> list[dict]:  # noqa: ARG002
        return []


class CockpitChartCommandTests(unittest.TestCase):
    def test_prepare_chart_args_equity_builds_csv(self):
        with tempfile.TemporaryDirectory() as td:
            args, err = prepare_chart_action_args(
                "BHP",
                parse_kv_args=_ActionRegistryStub.parse_kv_args,
                tool_router=_ToolRouterRows(),
                out_dir=Path(td) / "reports" / "candles",
            )
            self.assertIsNone(err)
            self.assertIsNotNone(args)
            assert args is not None
            self.assertEqual(args.get("mode_flag"), "-f")
            mode_value = str(args.get("mode_value", ""))
            self.assertIn("BHP_candles_1d.csv", mode_value)
            self.assertTrue(Path(mode_value).exists())

    def test_prepare_chart_args_equity_no_rows_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            args, err = prepare_chart_action_args(
                "BHP",
                parse_kv_args=_ActionRegistryStub.parse_kv_args,
                tool_router=_ToolRouterEmpty(),
                out_dir=Path(td) / "reports" / "candles",
            )
            self.assertIsNone(args)
            self.assertIsInstance(err, str)
            self.assertIn("no OHLC data for BHP", str(err))

    def test_prepare_chart_args_crypto_shorthand(self):
        with tempfile.TemporaryDirectory() as td:
            args, err = prepare_chart_action_args(
                "BTC 4h",
                parse_kv_args=_ActionRegistryStub.parse_kv_args,
                tool_router=_ToolRouterEmpty(),
                out_dir=Path(td) / "reports" / "candles",
            )
            self.assertIsNone(err)
            self.assertIsNotNone(args)
            assert args is not None
            self.assertEqual(args.get("mode_flag"), "-s")
            self.assertEqual(args.get("mode_value"), "BTC/USDT")
            self.assertEqual(args.get("timeframe"), "4h")


if __name__ == "__main__":
    unittest.main()
