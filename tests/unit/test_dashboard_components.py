"""``SentimentGauge`` / ``FinancialSummary`` / alerts 단위 테스트
(T-033, T-034, T-035, T-036, T-039)."""

from __future__ import annotations

import unittest

from semi_senti.dashboard.alerts import build_stale_message
from semi_senti.dashboard.data_provider import StaleStatus
from semi_senti.dashboard.financial_panel import (
    FinancialSummary,
    build_band_summary,
    format_metric_rows,
)
from semi_senti.dashboard.sentiment_gauge import (
    SentimentGauge,
    build_gauge_payload,
    build_keyword_rows,
)


# -----------------------------------------------------------------------------
# SentimentGauge
# -----------------------------------------------------------------------------


class TestGaugePayload(unittest.TestCase):
    def test_fear_payload(self) -> None:
        payload = build_gauge_payload(
            {
                "score": -78,
                "classification": {"key": "FEAR", "label_ko": "공포", "color": "#2563EB"},
                "news_count": 12,
                "score_date": "2026-05-15",
            }
        )
        self.assertEqual(payload["label_ko"], "공포")
        self.assertEqual(payload["color"], "#2563EB")
        # -78 → (-78 + 100)/2 = 11
        self.assertAlmostEqual(payload["score_pct"], 11.0)
        self.assertFalse(payload["is_unknown"])

    def test_unknown_payload(self) -> None:
        payload = build_gauge_payload({})
        self.assertTrue(payload["is_unknown"])
        self.assertAlmostEqual(payload["score_pct"], 50.0)

    def test_clamping(self) -> None:
        payload = build_gauge_payload({"score": 9999})
        self.assertLessEqual(payload["score_pct"], 100.0)
        payload = build_gauge_payload({"score": -9999})
        self.assertGreaterEqual(payload["score_pct"], 0.0)


class TestKeywordRows(unittest.TestCase):
    def test_direction_marks(self) -> None:
        rows = build_keyword_rows(
            [
                {"word": "감산", "weight": 2.0, "count": 4, "contribution": 8.0},
                {"word": "재고", "weight": -2.0, "count": 5, "contribution": -10.0},
            ]
        )
        self.assertEqual(rows[0]["direction"], "▲")
        self.assertEqual(rows[1]["direction"], "▼")

    def test_invalid_inputs_safe(self) -> None:
        rows = build_keyword_rows([{"word": None, "weight": "x", "count": "?", "contribution": "y"}])
        self.assertEqual(rows[0]["word"], "-")
        self.assertEqual(rows[0]["count"], 0)
        self.assertAlmostEqual(rows[0]["contribution"], 0.0)


class TestSentimentGaugeRefreshInterval(unittest.TestCase):
    def test_default_is_5_minutes(self) -> None:
        # T-034: 5분(300초) 자동 갱신.
        self.assertEqual(SentimentGauge().refresh_interval_seconds, 300)

    def test_invalid_interval_raises(self) -> None:
        with self.assertRaises(ValueError):
            SentimentGauge(refresh_interval_seconds=0)


# -----------------------------------------------------------------------------
# FinancialSummary
# -----------------------------------------------------------------------------


class TestFinancialFormatter(unittest.TestCase):
    def test_metric_rows_have_six_items(self) -> None:
        rows = format_metric_rows(
            {
                "current_price": 70000,
                "record_date": "2026-05-15",
                "revenue": 200_000_000_000_000,  # 200조
                "operating_profit": 25_000_000_000_000,
                "per": 10.0,
                "pbr": 1.2,
                "eps": 5000,
                "currency": "KRW",
            }
        )
        labels = [r[0] for r in rows]
        self.assertEqual(
            labels, ["현재가", "매출액", "영업이익", "PER", "PBR", "EPS"]
        )
        # 200조 단위로 축약되었는지 확인.
        revenue_value = next(r[1] for r in rows if r[0] == "매출액")
        self.assertIn("조 원", revenue_value)

    def test_metric_rows_handle_missing_values(self) -> None:
        rows = format_metric_rows({})
        for label, value, _ in rows:
            self.assertEqual(value, "N/A", msg=f"label={label} 가 N/A 가 아님")

    def test_band_summary_position(self) -> None:
        summary = build_band_summary(
            {"current_price": 75.0, "currency": "KRW"},
            {"band_low": 60.0, "band_high": 90.0, "band_mid": 75.0, "method": "per_eps"},
        )
        self.assertAlmostEqual(summary["band_position"], 0.0)  # 정확히 중앙
        self.assertAlmostEqual(summary["diff_low_pct"], 25.0)

    def test_columns_per_row_validation(self) -> None:
        with self.assertRaises(ValueError):
            FinancialSummary(columns_per_row=4)


# -----------------------------------------------------------------------------
# alerts.build_stale_message
# -----------------------------------------------------------------------------


class TestStaleMessage(unittest.TestCase):
    def test_fresh_data_no_banner(self) -> None:
        msg = build_stale_message(
            StaleStatus(is_stale=False, last_updated="2026-05-15 10:00:00", hours_old=1.0)
        )
        self.assertFalse(msg["show"])

    def test_warning_level(self) -> None:
        msg = build_stale_message(
            StaleStatus(
                is_stale=True,
                last_updated="2026-05-15 10:00:00",
                hours_old=10.0,
                message="외부 API 지연",
            )
        )
        self.assertTrue(msg["show"])
        self.assertEqual(msg["level"], "warning")

    def test_error_level_after_one_day(self) -> None:
        msg = build_stale_message(
            StaleStatus(
                is_stale=True,
                last_updated="2026-05-14 10:00:00",
                hours_old=30.0,
            )
        )
        self.assertEqual(msg["level"], "error")

    def test_no_data_is_error(self) -> None:
        msg = build_stale_message(StaleStatus(is_stale=True, last_updated=None))
        self.assertEqual(msg["level"], "error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
