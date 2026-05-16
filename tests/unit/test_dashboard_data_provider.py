"""``DataProvider`` 단위 테스트 (Phase 3, T-028 ~ T-039 데이터 어댑터 부분).

- 대시보드 UI 컴포넌트가 사용하는 데이터 형태/포맷이 계약대로 산출되는지 검증.
- Streamlit/차트 라이브러리 의존성 없음 — 순수 Python 만 사용.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.dashboard.data_provider import (
    DataProvider,
    StaleStatus,
    classify_sentiment,
)
from semi_senti.db import DBControl, init_database


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "dashboard_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        init_database(db_path=self.db_path)
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "005930", "name": "삼성전자", "market": "KOSPI"},
                conflict_columns=["stock_code"],
            )
            for i, date in enumerate(
                ["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
            ):
                db.upsert(
                    "financials",
                    {
                        "stock_code": "005930",
                        "record_date": date,
                        "open_price": 70000 + i * 100,
                        "high_price": 70200 + i * 100,
                        "low_price": 69800 + i * 100,
                        "close_price": 70000 + i * 100,
                        "volume": 1_000_000 + i,
                        "per": 10.0,
                        "pbr": 1.2,
                        "eps": 5000.0,
                        "revenue": 200_000_000_000_000,
                        "operating_profit": 25_000_000_000_000,
                        "currency": "KRW",
                    },
                    conflict_columns=["stock_code", "record_date"],
                )
            # 시그널 2건 (BUY 1, HOLD 1) — HOLD 는 마커에서 제외되어야 한다.
            db.insert(
                "signals",
                {
                    "stock_code": "005930",
                    "signal_type": "BUY",
                    "price": 70300.0,
                    "band_low": 75000.0,
                    "band_high": 95000.0,
                    "sentiment_score": -85.0,
                    "rationale": "test buy",
                    "signaled_at": "2026-05-15T10:00:00",
                },
            )
            db.insert(
                "signals",
                {
                    "stock_code": "005930",
                    "signal_type": "HOLD",
                    "price": 70000.0,
                    "band_low": 75000.0,
                    "band_high": 95000.0,
                    "sentiment_score": -10.0,
                    "rationale": "test hold",
                    "signaled_at": "2026-05-12T10:00:00",
                },
            )
            db.upsert(
                "sentiment_scores",
                {
                    "stock_code": "005930",
                    "score_date": "2026-05-15",
                    "score": -78.0,
                    "raw_score": -19.5,
                    "news_count": 12,
                    "top_keywords": json.dumps(
                        [
                            {"word": "감산", "weight": 2.0, "count": 4, "contribution": 8.0},
                            {"word": "재고", "weight": -2.0, "count": 5, "contribution": -10.0},
                        ],
                        ensure_ascii=False,
                    ),
                },
                conflict_columns=["stock_code", "score_date"],
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


class TestClassifySentiment(unittest.TestCase):
    def test_fear(self) -> None:
        self.assertEqual(classify_sentiment(-80)["key"], "FEAR")
        self.assertEqual(classify_sentiment(-34)["key"], "FEAR")

    def test_neutral(self) -> None:
        self.assertEqual(classify_sentiment(0)["key"], "NEUTRAL")
        self.assertEqual(classify_sentiment(33)["key"], "NEUTRAL")

    def test_greed(self) -> None:
        self.assertEqual(classify_sentiment(34)["key"], "GREED")
        self.assertEqual(classify_sentiment(100)["key"], "GREED")

    def test_unknown(self) -> None:
        self.assertEqual(classify_sentiment(None)["key"], "UNKNOWN")
        self.assertEqual(classify_sentiment("not-a-number")["key"], "UNKNOWN")


class TestDataProviderQueries(_Base):
    def test_list_active_stocks(self) -> None:
        with DataProvider() as dp:
            stocks = dp.list_active_stocks()
        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0]["stock_code"], "005930")
        self.assertEqual(stocks[0]["name"], "삼성전자")

    def test_fetch_candles_orders_ascending(self) -> None:
        with DataProvider() as dp:
            candles = dp.fetch_candles("005930", limit=10)
        self.assertEqual(len(candles), 4)
        # 오름차순(과거 → 최신).
        times = [c["time"] for c in candles]
        self.assertEqual(times, sorted(times))
        self.assertIn("open", candles[0])
        self.assertIn("close", candles[0])

    def test_fetch_signals_excludes_hold(self) -> None:
        with DataProvider() as dp:
            markers = dp.fetch_signals("005930")
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["signal_type"], "BUY")
        # T-031 hover tooltip 에 감성/현재가 등이 포함되어야 함.
        self.assertIn("감성", markers[0]["tooltip"])

    def test_fetch_sentiment_payload(self) -> None:
        with DataProvider() as dp:
            sent = dp.fetch_sentiment("005930")
        self.assertAlmostEqual(sent["score"], -78.0)
        self.assertEqual(sent["news_count"], 12)
        self.assertEqual(sent["classification"]["key"], "FEAR")
        self.assertEqual(sent["top_keywords"][0]["word"], "감산")

    def test_fetch_financial_summary(self) -> None:
        with DataProvider() as dp:
            fin = dp.fetch_financial_summary("005930")
        self.assertEqual(fin["currency"], "KRW")
        self.assertAlmostEqual(fin["per"], 10.0)
        self.assertAlmostEqual(fin["eps"], 5000.0)
        self.assertIsNotNone(fin["revenue"])
        self.assertEqual(fin["record_date"], "2026-05-15")

    def test_fetch_band_per_eps(self) -> None:
        with DataProvider() as dp:
            band = dp.fetch_band("005930")
        self.assertEqual(band["method"], "per_eps")
        self.assertGreater(band["band_high"], band["band_low"])

    def test_compute_stale_status_recent_data(self) -> None:
        # 방금 INSERT 했으므로 stale 이 아니어야 함.
        with DataProvider(stale_after_hours=24) as dp:
            stale = dp.compute_stale_status("005930")
        self.assertIsInstance(stale, StaleStatus)
        self.assertFalse(stale.is_stale)
        self.assertIsNotNone(stale.last_updated)

    def test_get_snapshot_assembles_all_blocks(self) -> None:
        with DataProvider() as dp:
            snapshot = dp.get_snapshot("005930")
        self.assertEqual(snapshot.stock_code, "005930")
        self.assertEqual(snapshot.stock_name, "삼성전자")
        self.assertGreater(len(snapshot.candles), 0)
        self.assertEqual(len(snapshot.signals), 1)
        self.assertIn("score", snapshot.sentiment)
        self.assertIn("per", snapshot.financial)
        self.assertIn("band_high", snapshot.band)


if __name__ == "__main__":
    unittest.main(verbosity=2)
