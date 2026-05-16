"""``CycleAnalyzer`` 단위 테스트 (Phase 4-2, T-044, T-045)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.db import DBControl, init_database
from semi_senti.engine import (
    CycleAnalyzer,
    classify_phase,
    compute_cycle_score,
)


class TestPureFunctions(unittest.TestCase):
    def test_classify_phase_thresholds(self) -> None:
        self.assertEqual(classify_phase(-90), "TROUGH")
        self.assertEqual(classify_phase(-30), "EARLY_CYCLE")
        self.assertEqual(classify_phase(0), "MID_CYCLE")
        self.assertEqual(classify_phase(40), "LATE_CYCLE")
        self.assertEqual(classify_phase(80), "PEAK")

    def test_classify_phase_clamps_extreme(self) -> None:
        self.assertEqual(classify_phase(9999), "PEAK")
        self.assertEqual(classify_phase(-9999), "TROUGH")
        self.assertEqual(classify_phase(None), "MID_CYCLE")

    def test_compute_score_returns_none_when_all_missing(self) -> None:
        self.assertIsNone(
            compute_cycle_score(
                inventory_turnover=None,
                revenue_growth_pct=None,
                op_margin_pct=None,
            )
        )

    def test_compute_score_balanced(self) -> None:
        # 모든 입력이 target 이면 점수 ≈ 0
        score = compute_cycle_score(
            inventory_turnover=4.0,
            revenue_growth_pct=0.0,
            op_margin_pct=10.0,
        )
        self.assertIsNotNone(score)
        self.assertAlmostEqual(score, 0.0, places=2)

    def test_compute_score_strong_growth(self) -> None:
        # 강한 상승 신호 → +방향
        score = compute_cycle_score(
            inventory_turnover=6.0,        # +1.0
            revenue_growth_pct=20.0,       # +1.0
            op_margin_pct=25.0,            # +1.0
        )
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 90.0)

    def test_compute_score_weakness(self) -> None:
        score = compute_cycle_score(
            inventory_turnover=2.0,        # -1.0
            revenue_growth_pct=-20.0,      # -1.0
            op_margin_pct=-5.0,            # -1.0
        )
        self.assertIsNotNone(score)
        self.assertLessEqual(score, -90.0)


class _DBBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "cycle.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        init_database(db_path=self.db_path)
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "005930", "name": "삼성전자", "market": "KOSPI"},
                conflict_columns=["stock_code"],
            )
            # 1년 전 분기 보고
            db.upsert(
                "financials",
                {
                    "stock_code": "005930",
                    "record_date": "2025-05-15",
                    "close_price": 70000,
                    "revenue": 100_000_000_000_000,   # 100조
                    "operating_profit": 5_000_000_000_000,  # 5%
                },
                conflict_columns=["stock_code", "record_date"],
            )
            # 최신 분기 보고 (전년比 +20%, 영업이익률 10%)
            db.upsert(
                "financials",
                {
                    "stock_code": "005930",
                    "record_date": "2026-05-15",
                    "close_price": 80000,
                    "revenue": 120_000_000_000_000,
                    "operating_profit": 12_000_000_000_000,
                },
                conflict_columns=["stock_code", "record_date"],
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        os.environ.pop("SEMI_SENTI_SQLITE_PATH", None)


class TestCycleAnalyzerDB(_DBBase):
    def test_compute_from_db_uses_yoy_growth(self) -> None:
        with CycleAnalyzer() as ca:
            result = ca.compute_from_db("005930")
        self.assertEqual(result.stock_code, "005930")
        # YoY 매출 성장률 = (120 - 100) / 100 * 100 = 20%
        self.assertAlmostEqual(result.revenue_growth_pct, 20.0, places=2)
        # 영업이익률 = 12 / 120 * 100 = 10%
        self.assertAlmostEqual(result.op_margin_pct, 10.0, places=2)
        # phase 가 MID_CYCLE 또는 LATE_CYCLE 사이여야 함
        self.assertIn(result.phase, ("MID_CYCLE", "LATE_CYCLE"))

    def test_analyze_and_store_persists_row(self) -> None:
        with CycleAnalyzer() as ca:
            result = ca.analyze_and_store("005930")
            latest = ca.latest("005930")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["phase"], result.phase)
        self.assertAlmostEqual(latest["cycle_score"], result.cycle_score, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
