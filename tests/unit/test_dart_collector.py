"""``DartFinancialCollector`` 단위 테스트 (T-005, T-006, T-009)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from semi_senti.collector.dart import DartFinancialCollector
from semi_senti.db import DBControl, init_database


_FAKE_ACCOUNT_ROWS = [
    {"account_nm": "매출액", "thstrm_amount": "300,000,000"},
    {"account_nm": "영업이익", "thstrm_amount": "(50,000)"},
    {"account_nm": "기타", "thstrm_amount": "999"},
]

_FAKE_INDEX_ROWS = [
    {"idx_nm": "주당순이익(EPS)", "idx_val": "8,500"},
    {"idx_nm": "주가수익비율(PER)", "idx_val": "12.3"},
    {"idx_nm": "주가순자산비율(PBR)", "idx_val": "1.4"},
]


class TestDartFinancialCollector(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "dart_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        os.environ["OPEN_DART_API_KEY"] = "DUMMY_DART_KEY"
        init_database(db_path=self.db_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ---- parser 단위 ----
    def test_parse_account_rows(self) -> None:
        parsed = DartFinancialCollector.parse_account_rows(_FAKE_ACCOUNT_ROWS)
        self.assertEqual(parsed["revenue"], 300000000.0)
        self.assertEqual(parsed["operating_profit"], -50000.0)

    def test_parse_index_rows(self) -> None:
        parsed = DartFinancialCollector.parse_index_rows(_FAKE_INDEX_ROWS)
        self.assertEqual(parsed["eps"], 8500.0)
        self.assertEqual(parsed["per"], 12.3)
        self.assertEqual(parsed["pbr"], 1.4)

    # ---- API 키 검증 ----
    def test_missing_api_key_raises(self) -> None:
        os.environ["OPEN_DART_API_KEY"] = ""
        from semi_senti.collector import CollectorError

        with DartFinancialCollector() as dc:
            with self.assertRaises(CollectorError):
                dc._require_api_key()
        os.environ["OPEN_DART_API_KEY"] = "DUMMY_DART_KEY"

    # ---- collect_and_store 통합 ----
    def test_collect_and_store_full_flow(self) -> None:
        with patch.object(
            DartFinancialCollector,
            "fetch_single_company_account",
            return_value=_FAKE_ACCOUNT_ROWS,
        ), patch.object(
            DartFinancialCollector,
            "fetch_single_company_index",
            return_value=_FAKE_INDEX_ROWS,
        ):
            with DartFinancialCollector() as dc:
                record = dc.collect_and_store(
                    stock_code="005930",
                    corp_code="00126380",
                    bsns_year="2025",
                    stock_name="삼성전자",
                    record_date="2026-05-16",
                )
        self.assertEqual(record["stock_code"], "005930")
        self.assertEqual(record["revenue"], 300000000.0)
        self.assertEqual(record["operating_profit"], -50000.0)

        with DBControl(db_path=self.db_path) as db:
            stored = db.fetch_one(
                "SELECT revenue, operating_profit, per, pbr, eps "
                "FROM financials WHERE stock_code = ?",
                ("005930",),
            )
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["revenue"], 300000000.0)
        self.assertEqual(stored["per"], 12.3)

    def test_collect_falls_back_to_cache_on_api_failure(self) -> None:
        """API 실패 시 캐시된 직전 row 로 폴백 (F-1.3.3)."""
        # 1) 우선 캐시 형성
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
                    "record_date": "2026-05-15",
                    "revenue": 1.0,
                    "operating_profit": 2.0,
                    "per": 10.0,
                    "pbr": 1.0,
                    "eps": 5.0,
                },
                conflict_columns=["stock_code", "record_date"],
            )

        def _boom(*args, **kwargs):
            raise RuntimeError("simulate DART network failure")

        with patch.object(
            DartFinancialCollector, "fetch_single_company_account", side_effect=_boom
        ):
            with DartFinancialCollector() as dc:
                record = dc.collect_and_store(
                    stock_code="005930",
                    corp_code="00126380",
                    bsns_year="2025",
                    stock_name="삼성전자",
                    record_date="2026-05-16",
                )
        # 폴백된 결과가 정상화되어 적재되었는지 확인.
        self.assertEqual(record["revenue"], 1.0)
        self.assertEqual(record["per"], 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
