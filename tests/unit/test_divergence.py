"""``DivergenceDetector`` 단위 테스트 (T-026, T-027)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.db import DBControl, init_database
from semi_senti.engine import DivergenceDetector


class TestDivergenceDetector(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "div_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        os.environ["DIVERGENCE_PRICE_THRESHOLD"] = "2.0"
        os.environ["DIVERGENCE_SENTIMENT_THRESHOLD"] = "10.0"
        os.environ["DIVERGENCE_WINDOW_DAYS"] = "3"
        init_database(db_path=self.db_path)

        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks", {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ----- 순수 함수 검증 (DB 무관) -----
    def test_pure_bullish(self) -> None:
        dd = DivergenceDetector()
        res = dd._evaluate(
            stock_code="X",
            price_series=[100.0, 98.0, 95.0],          # -5%
            sentiment_series=[10.0, 20.0, 30.0],        # +20pt
            window_days=3,
        )
        self.assertEqual(res.divergence_type, "BULLISH_OPPORTUNITY")
        self.assertTrue(res.detected)

    def test_pure_bearish(self) -> None:
        dd = DivergenceDetector()
        res = dd._evaluate(
            stock_code="X",
            price_series=[100.0, 102.0, 105.0],          # +5%
            sentiment_series=[50.0, 40.0, 30.0],         # -20pt
            window_days=3,
        )
        self.assertEqual(res.divergence_type, "BEARISH_CAUTION")

    def test_same_direction_is_none(self) -> None:
        dd = DivergenceDetector()
        res = dd._evaluate(
            stock_code="X",
            price_series=[100.0, 102.0, 105.0],          # +5%
            sentiment_series=[10.0, 20.0, 30.0],         # +20pt
            window_days=3,
        )
        self.assertEqual(res.divergence_type, "NONE")

    def test_below_threshold_is_none(self) -> None:
        dd = DivergenceDetector()
        # 주가 변화 0.5% < 2% 임계값 → NONE
        res = dd._evaluate(
            stock_code="X",
            price_series=[100.0, 100.5],
            sentiment_series=[10.0, 50.0],
            window_days=2,
        )
        self.assertEqual(res.divergence_type, "NONE")

    def test_short_series_is_none(self) -> None:
        dd = DivergenceDetector()
        res = dd._evaluate(
            stock_code="X",
            price_series=[100.0],
            sentiment_series=[10.0],
            window_days=2,
        )
        self.assertEqual(res.divergence_type, "NONE")
        self.assertEqual(res.note, "데이터 부족")

    # ----- DB 통합 -----
    def test_detect_via_db(self) -> None:
        with DBControl(db_path=self.db_path) as db:
            # 주가는 하락, 감성은 상승 → BULLISH
            for date, price in zip(
                ["2026-05-13", "2026-05-14", "2026-05-15"],
                [100.0, 96.0, 92.0],
            ):
                db.upsert(
                    "financials",
                    {"stock_code": "005930", "record_date": date, "close_price": price},
                    conflict_columns=["stock_code", "record_date"],
                )
            for date, score in zip(
                ["2026-05-13", "2026-05-14", "2026-05-15"],
                [-30.0, -10.0, 20.0],
            ):
                db.upsert(
                    "sentiment_scores",
                    {"stock_code": "005930", "score_date": date,
                     "score": score, "raw_score": score / 10, "news_count": 5},
                    conflict_columns=["stock_code", "score_date"],
                )

        with DivergenceDetector() as dd:
            res = dd.detect("005930", window_days=3)
        self.assertEqual(res.divergence_type, "BULLISH_OPPORTUNITY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
