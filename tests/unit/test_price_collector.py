"""``PriceCollector`` 단위 테스트 (T-007, T-009).

yfinance 자체를 호출하지 않고 ``_fetch_history`` 를 monkeypatch 한다.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from semi_senti.collector.price import PriceCollector
from semi_senti.db import DBControl, init_database


_FAKE_HISTORY = [
    {
        "record_date": "2026-05-13",
        "open": 70000.0,
        "high": 71500.0,
        "low": 69500.0,
        "close": 71000.0,
        "volume": 12345678,
    },
    {
        "record_date": "2026-05-14",
        "open": 71000.0,
        "high": 72000.0,
        "low": 70500.0,
        "close": 71800.0,
        "volume": 23456789,
    },
    {
        "record_date": "2026-05-15",
        "open": 71800.0,
        "high": 72500.0,
        "low": 71200.0,
        "close": 72200.0,
        "volume": 34567890,
    },
]


class TestPriceCollector(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "price_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        os.environ["PRICE_CACHE_TTL_MINUTES"] = "60"
        init_database(db_path=self.db_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_to_yahoo_symbol(self) -> None:
        self.assertEqual(PriceCollector.to_yahoo_symbol("005930", "KOSPI"), "005930.KS")
        self.assertEqual(PriceCollector.to_yahoo_symbol("035720", "KOSDAQ"), "035720.KQ")
        self.assertEqual(PriceCollector.to_yahoo_symbol("005930.KS"), "005930.KS")
        from semi_senti.collector import CollectorError

        with self.assertRaises(CollectorError):
            PriceCollector.to_yahoo_symbol("005930", "NYSE")

    def test_collect_and_store_inserts_rows(self) -> None:
        with patch.object(PriceCollector, "_fetch_history", return_value=_FAKE_HISTORY):
            with PriceCollector() as pc:
                count = pc.collect_and_store(
                    stock_code="005930",
                    market="KOSPI",
                    stock_name="삼성전자",
                    force=True,
                )
        self.assertEqual(count, 3)

        with DBControl(db_path=self.db_path) as db:
            rows = db.fetch_all(
                "SELECT record_date, close_price, volume FROM financials "
                "WHERE stock_code = ? ORDER BY record_date",
                ("005930",),
            )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["close_price"], 72200.0)
        self.assertEqual(rows[-1]["volume"], 34567890)

    def test_collect_preserves_existing_financials(self) -> None:
        """주가 적재 시 기존 재무 컬럼(revenue 등)이 NULL 로 덮어쓰이지 않아야 한다."""
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )
            db.upsert(
                "financials",
                {
                    "stock_code": "005930",
                    "record_date": "2026-05-13",
                    "revenue": 999.0,
                    "per": 12.3,
                },
                conflict_columns=["stock_code", "record_date"],
            )

        with patch.object(PriceCollector, "_fetch_history", return_value=_FAKE_HISTORY):
            with PriceCollector() as pc:
                pc.collect_and_store(
                    stock_code="005930",
                    market="KOSPI",
                    stock_name="삼성전자",
                    force=True,
                )

        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT revenue, per, close_price FROM financials "
                "WHERE stock_code = ? AND record_date = ?",
                ("005930", "2026-05-13"),
            )
        self.assertIsNotNone(row)
        assert row is not None
        # 주가 컬럼은 갱신, 재무 컬럼은 보존되어야 함.
        self.assertEqual(row["close_price"], 71000.0)
        self.assertEqual(row["revenue"], 999.0)
        self.assertEqual(row["per"], 12.3)

    def test_cache_skip_when_fresh(self) -> None:
        """TTL 신선 시 _fetch_history 호출 안 됨."""
        with patch.object(PriceCollector, "_fetch_history", return_value=_FAKE_HISTORY):
            with PriceCollector() as pc:
                pc.collect_and_store(
                    stock_code="005930", market="KOSPI", stock_name="삼성전자", force=True
                )

        with patch.object(PriceCollector, "_fetch_history") as mocked:
            with PriceCollector() as pc:
                count = pc.collect_and_store(
                    stock_code="005930", market="KOSPI", stock_name="삼성전자", force=False
                )
            mocked.assert_not_called()
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
