"""``StockAdmin`` / ``SystemMonitor`` 단위 테스트 (Phase 4-3, T-046, T-047)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.admin import StockAdmin, StockAdminError, SystemMonitor
from semi_senti.db import DBControl, init_database


class _DBBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "admin.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        init_database(db_path=self.db_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        os.environ.pop("SEMI_SENTI_SQLITE_PATH", None)


class TestStockAdminValidation(unittest.TestCase):
    def test_validate_stock_code_accepts_six_digits(self) -> None:
        self.assertEqual(StockAdmin.validate_stock_code(" 005930 "), "005930")

    def test_validate_stock_code_rejects_invalid(self) -> None:
        for bad in ("12345", "AAPL", "1234567", "00593a", ""):
            with self.assertRaises(StockAdminError, msg=bad):
                StockAdmin.validate_stock_code(bad)

    def test_normalize_market(self) -> None:
        self.assertEqual(StockAdmin.normalize_market("kospi"), "KOSPI")
        self.assertEqual(StockAdmin.normalize_market("KOSDAQ"), "KOSDAQ")
        with self.assertRaises(StockAdminError):
            StockAdmin.normalize_market("NYSE")


class TestStockAdminCRUD(_DBBase):
    def test_add_stock_without_yfinance(self) -> None:
        with StockAdmin() as admin:
            row = admin.add_stock(
                stock_code="005930",
                name="삼성전자",
                market="KOSPI",
                validate_with_yfinance=False,
            )
        self.assertEqual(row["stock_code"], "005930")
        self.assertEqual(row["is_active"], 1)

    def test_update_stock(self) -> None:
        with StockAdmin() as admin:
            admin.add_stock(
                stock_code="000660", name="SK하이닉스",
                market="KOSPI", validate_with_yfinance=False,
            )
            affected = admin.update_stock(stock_code="000660", name="SK Hynix")
        self.assertEqual(affected, 1)
        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT name FROM stocks WHERE stock_code = ?", ("000660",)
            )
        self.assertEqual(row["name"], "SK Hynix")

    def test_deactivate_then_list(self) -> None:
        with StockAdmin() as admin:
            admin.add_stock(
                stock_code="000660", name="SK하이닉스",
                market="KOSPI", validate_with_yfinance=False,
            )
            admin.deactivate_stock("000660")
            active_only = admin.list_stocks()
            with_inactive = admin.list_stocks(include_inactive=True)
        self.assertEqual(len(active_only), 0)
        self.assertEqual(len(with_inactive), 1)
        self.assertEqual(with_inactive[0]["is_active"], 0)

    def test_delete_cascade(self) -> None:
        with DBControl(db_path=self.db_path) as db:
            # 종목 직접 등록 + 관련 row 추가
            db.upsert(
                "stocks", {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )
            db.upsert(
                "financials",
                {"stock_code": "005930", "record_date": "2026-05-15", "close_price": 70000},
                conflict_columns=["stock_code", "record_date"],
            )
        with StockAdmin() as admin:
            admin.delete_stock("005930", cascade=True)
        with DBControl(db_path=self.db_path) as db:
            stock = db.fetch_one(
                "SELECT * FROM stocks WHERE stock_code = ?", ("005930",)
            )
            child = db.fetch_one(
                "SELECT * FROM financials WHERE stock_code = ?", ("005930",)
            )
        self.assertIsNone(stock)
        self.assertIsNone(child)

    def test_delete_nonexistent_raises(self) -> None:
        with StockAdmin() as admin:
            with self.assertRaises(StockAdminError):
                admin.delete_stock("999999", cascade=True)


class TestSystemMonitor(_DBBase):
    def test_status_report_with_no_stocks(self) -> None:
        with SystemMonitor() as monitor:
            report = monitor.status_report()
        self.assertEqual(report.table_counts.get("stocks"), 0)
        self.assertEqual(report.failed_notifications, 0)
        self.assertEqual(report.stocks, [])

    def test_status_report_summarizes_each_stock(self) -> None:
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks", {"stock_code": "005930", "name": "삼성전자", "market": "KOSPI"},
                conflict_columns=["stock_code"],
            )
            db.upsert(
                "financials",
                {"stock_code": "005930", "record_date": "2026-05-15", "close_price": 70000},
                conflict_columns=["stock_code", "record_date"],
            )
            db.insert(
                "signals",
                {"stock_code": "005930", "signal_type": "BUY", "price": 70000,
                 "signaled_at": "2026-05-15T10:00:00"},
            )
        with SystemMonitor() as monitor:
            report = monitor.status_report()
        self.assertEqual(len(report.stocks), 1)
        summary = report.stocks[0]
        self.assertEqual(summary.stock_code, "005930")
        self.assertEqual(summary.signal_count, 1)
        self.assertIsNotNone(summary.last_price_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)
