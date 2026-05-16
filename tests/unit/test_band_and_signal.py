"""``FundamentalBand`` + ``SignalLogic`` 단위 테스트 (T-022, T-023, T-024, T-025)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.db import DBControl, init_database
from semi_senti.engine import FundamentalBand, SignalLogic
from semi_senti.engine.band import Band


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "band_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        # 시그널 임계값 명시 (PRD §F-3.2)
        os.environ["SIGNAL_SENTIMENT_BUY_THRESHOLD"] = "-70"
        os.environ["SIGNAL_SENTIMENT_SELL_THRESHOLD"] = "70"
        os.environ["BAND_MARGIN"] = "0.15"
        init_database(db_path=self.db_path)

        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks", {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


class TestFundamentalBand(_Base):
    def test_per_eps_method(self) -> None:
        # PER 평균이 일정하고 최신 EPS 가 있는 케이스 → per_eps 방식.
        with DBControl(db_path=self.db_path) as db:
            for i, date in enumerate(["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]):
                db.upsert(
                    "financials",
                    {
                        "stock_code": "005930",
                        "record_date": date,
                        "close_price": 70000 + i * 100,
                        "per": 10.0,
                        "eps": 5000.0,
                    },
                    conflict_columns=["stock_code", "record_date"],
                )

        with FundamentalBand() as fb:
            band = fb.compute("005930")
        self.assertEqual(band.method, "per_eps")
        self.assertIsNotNone(band.band_mid)
        assert band.band_mid is not None
        self.assertAlmostEqual(band.band_mid, 10.0 * 5000.0)
        assert band.band_low is not None and band.band_high is not None
        self.assertAlmostEqual(band.band_low, 50000 * 0.85)
        self.assertAlmostEqual(band.band_high, 50000 * 1.15)

    def test_price_quantile_fallback(self) -> None:
        # PER/EPS 없음 → 종가 분위 사용.
        with DBControl(db_path=self.db_path) as db:
            for i, date in enumerate(["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]):
                db.upsert(
                    "financials",
                    {"stock_code": "005930", "record_date": date,
                     "close_price": 1000 + i * 100},
                    conflict_columns=["stock_code", "record_date"],
                )

        with FundamentalBand() as fb:
            band = fb.compute("005930")
        self.assertEqual(band.method, "price_quantile")
        assert band.band_low is not None and band.band_high is not None
        self.assertLess(band.band_low, band.band_high)

    def test_unavailable_when_no_rows(self) -> None:
        with FundamentalBand() as fb:
            band = fb.compute("005930")
        self.assertEqual(band.method, "unavailable")
        self.assertFalse(band.is_valid)


class TestSignalLogic(_Base):
    def _make_band(self, low: float, high: float) -> Band:
        return Band(
            stock_code="005930", band_low=low, band_high=high,
            band_mid=(low + high) / 2, method="per_eps", sample_size=5,
        )

    def test_decide_buy(self) -> None:
        # PRD §F-3.2: 현재가 < band_low AND sentiment < -70
        with SignalLogic() as sl:
            dec = sl.decide(
                stock_code="005930", price=50.0,
                band=self._make_band(60.0, 90.0), sentiment_score=-80.0,
            )
        self.assertEqual(dec.signal_type, "BUY")

    def test_decide_sell(self) -> None:
        # 현재가 > band_high AND sentiment > +70
        with SignalLogic() as sl:
            dec = sl.decide(
                stock_code="005930", price=100.0,
                band=self._make_band(60.0, 90.0), sentiment_score=80.0,
            )
        self.assertEqual(dec.signal_type, "SELL")

    def test_decide_hold_inside_band(self) -> None:
        with SignalLogic() as sl:
            dec = sl.decide(
                stock_code="005930", price=75.0,
                band=self._make_band(60.0, 90.0), sentiment_score=-80.0,
            )
        self.assertEqual(dec.signal_type, "HOLD")

    def test_decide_hold_when_sentiment_below_threshold(self) -> None:
        with SignalLogic() as sl:
            dec = sl.decide(
                stock_code="005930", price=50.0,
                band=self._make_band(60.0, 90.0), sentiment_score=-50.0,
            )
        self.assertEqual(dec.signal_type, "HOLD")

    def test_decide_hold_on_missing_data(self) -> None:
        with SignalLogic() as sl:
            dec = sl.decide(
                stock_code="005930", price=None,
                band=self._make_band(60.0, 90.0), sentiment_score=-80.0,
            )
        self.assertEqual(dec.signal_type, "HOLD")

    def test_detect_and_store_persists_row(self) -> None:
        # 시그널 산출 + 적재 통합.
        with DBControl(db_path=self.db_path) as db:
            for i, date in enumerate(["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]):
                db.upsert(
                    "financials",
                    {"stock_code": "005930", "record_date": date,
                     "close_price": 30.0, "per": 10.0, "eps": 5.0},
                    conflict_columns=["stock_code", "record_date"],
                )
            db.upsert(
                "sentiment_scores",
                {"stock_code": "005930", "score_date": "2026-05-15",
                 "score": -85.0, "raw_score": -20.0, "news_count": 3},
                conflict_columns=["stock_code", "score_date"],
            )

        with SignalLogic() as sl:
            dec = sl.detect_and_store("005930")
        self.assertEqual(dec.signal_type, "BUY")

        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT signal_type, sentiment_score FROM signals WHERE stock_code = ? "
                "ORDER BY signaled_at DESC LIMIT 1", ("005930",),
            )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["signal_type"], "BUY")
        self.assertEqual(row["sentiment_score"], -85.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
