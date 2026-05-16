"""``SignalChart`` / chart builder 단위 테스트 (T-028 ~ T-032)."""

from __future__ import annotations

import unittest

from semi_senti.dashboard.chart import (
    SignalChart,
    build_band_lines,
    build_chart_options,
    build_divergence_markers,
    build_signal_markers,
)


class TestSignalMarkers(unittest.TestCase):
    def test_buy_marker_is_green_below_bar(self) -> None:
        markers = build_signal_markers(
            [
                {
                    "time": "2026-05-15",
                    "signal_type": "BUY",
                    "rationale": "test",
                    "tooltip": "감성 -82",
                }
            ]
        )
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m["text"], "BUY")
        self.assertEqual(m["position"], "belowBar")
        self.assertEqual(m["shape"], "arrowUp")
        # 녹색
        self.assertEqual(m["color"], "#16A34A")
        self.assertEqual(m["tooltip"], "감성 -82")

    def test_sell_marker_is_red_above_bar(self) -> None:
        markers = build_signal_markers(
            [{"time": "2026-05-15", "signal_type": "SELL", "tooltip": "감성 +85"}]
        )
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m["position"], "aboveBar")
        self.assertEqual(m["shape"], "arrowDown")
        # 적색
        self.assertEqual(m["color"], "#DC2626")

    def test_hold_marker_is_filtered_out(self) -> None:
        markers = build_signal_markers(
            [
                {"time": "2026-05-12", "signal_type": "HOLD"},
                {"time": "2026-05-13", "signal_type": "BUY"},
            ]
        )
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["signal_type"] if "signal_type" in markers[0] else markers[0]["text"], "BUY")

    def test_invalid_input_returns_empty(self) -> None:
        self.assertEqual(build_signal_markers([]), [])
        self.assertEqual(build_signal_markers(None), [])  # type: ignore[arg-type]


class TestDivergenceMarkers(unittest.TestCase):
    def test_bullish_marker_is_yellow(self) -> None:
        markers = build_divergence_markers(
            [
                {
                    "time": "2026-05-15",
                    "divergence_type": "BULLISH_OPPORTUNITY",
                    "tooltip": "기회",
                }
            ]
        )
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["color"], "#FBBF24")
        self.assertIn("기회", markers[0]["text"])

    def test_bearish_marker_is_purple(self) -> None:
        markers = build_divergence_markers(
            [
                {
                    "time": "2026-05-15",
                    "divergence_type": "BEARISH_CAUTION",
                    "tooltip": "주의",
                }
            ]
        )
        self.assertEqual(markers[0]["color"], "#8B5CF6")
        self.assertIn("주의", markers[0]["text"])

    def test_unknown_type_filtered(self) -> None:
        markers = build_divergence_markers(
            [{"time": "2026-05-15", "divergence_type": "NONE"}]
        )
        self.assertEqual(markers, [])


class TestBandLines(unittest.TestCase):
    def test_lines_emitted_only_when_band_present(self) -> None:
        candles = [
            {"time": "2026-05-12", "open": 1, "high": 1, "low": 1, "close": 1},
            {"time": "2026-05-15", "open": 1, "high": 1, "low": 1, "close": 1},
        ]
        lines = build_band_lines(candles, {"band_low": 60.0, "band_high": 90.0, "band_mid": 75.0})
        self.assertEqual(len(lines["high"]), 2)
        self.assertEqual(lines["high"][0]["value"], 90.0)
        self.assertEqual(lines["low"][-1]["value"], 60.0)

    def test_no_band_returns_empty(self) -> None:
        candles = [{"time": "2026-05-12", "open": 1, "high": 1, "low": 1, "close": 1}]
        lines = build_band_lines(
            candles, {"band_low": None, "band_high": None, "band_mid": None}
        )
        self.assertEqual(lines, {"high": [], "mid": [], "low": []})


class TestSignalChartBuild(unittest.TestCase):
    def test_build_includes_candlestick_series(self) -> None:
        chart = SignalChart(height=400)
        options = chart.build(
            candles=[
                {"time": "2026-05-12", "open": 100, "high": 110, "low": 95, "close": 105},
                {"time": "2026-05-13", "open": 105, "high": 115, "low": 100, "close": 112},
            ],
            signals=[
                {
                    "time": "2026-05-13",
                    "signal_type": "BUY",
                    "tooltip": "감성 -85",
                }
            ],
            divergences=[],
            band={"band_low": 95.0, "band_high": 115.0, "band_mid": 105.0},
        )
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["chart"]["height"], 400)
        types = [s["type"] for s in options[0]["series"]]
        self.assertIn("Candlestick", types)
        self.assertEqual(types.count("Line"), 3)  # high/mid/low band lines

        candlestick = next(s for s in options[0]["series"] if s["type"] == "Candlestick")
        self.assertEqual(len(candlestick["markers"]), 1)
        self.assertEqual(candlestick["markers"][0]["text"], "BUY")

    def test_build_chart_options_helper(self) -> None:
        options = build_chart_options(
            candles=[],
            signals=[],
            divergences=[],
            band={},
            chart_height=300,
        )
        self.assertEqual(options[0]["chart"]["height"], 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
