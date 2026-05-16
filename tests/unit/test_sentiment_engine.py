"""``SentimentEngine`` 단위 테스트 (T-015, T-018, T-019, T-020)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from semi_senti.db import DBControl, init_database
from semi_senti.engine import SentimentEngine


class TestSentimentEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "sent_test.db"
        os.environ["SEMI_SENTI_SQLITE_PATH"] = str(self.db_path)
        os.environ["SENTIMENT_NORMALIZATION_K"] = "10"
        init_database(db_path=self.db_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ----- normalize (T-019) -----
    def test_normalize_zero(self) -> None:
        eng = SentimentEngine()
        self.assertAlmostEqual(eng.normalize(0), 0.0, places=5)

    def test_normalize_bounds(self) -> None:
        eng = SentimentEngine()
        self.assertGreater(eng.normalize(1000), 99.0)
        self.assertLess(eng.normalize(-1000), -99.0)

    def test_normalize_monotonic(self) -> None:
        eng = SentimentEngine()
        self.assertLess(eng.normalize(5), eng.normalize(10))
        self.assertLess(eng.normalize(-10), eng.normalize(-5))

    # ----- analyze_text -----
    def test_analyze_positive_text(self) -> None:
        eng = SentimentEngine()
        result = eng.analyze_text("HBM 수요 증가, 감산 효과로 흑자 전환")
        self.assertGreater(result.score, 0)
        self.assertGreater(result.raw_score, 0)
        words = {h.word for h in result.hits}
        self.assertTrue({"hbm", "수요", "감산", "흑자전환"} & words)

    def test_analyze_negative_text(self) -> None:
        eng = SentimentEngine()
        result = eng.analyze_text("공급과잉 우려, 재고 증가와 가격 하락 지속")
        self.assertLess(result.score, 0)
        self.assertLess(result.raw_score, 0)

    def test_analyze_empty_text(self) -> None:
        eng = SentimentEngine()
        result = eng.analyze_text("")
        self.assertEqual(result.score, 0)
        self.assertEqual(result.news_count, 0)

    # ----- score_news_and_store (T-020) -----
    def test_score_news_and_store_aggregates(self) -> None:
        # 1) 종목 + 뉴스 row 직접 적재
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )
            db.insert(
                "news",
                {
                    "stock_code": "005930",
                    "title": "HBM 수요 폭증",
                    "summary": "감산 효과로 흑자 전환",
                    "cleaned_text": "HBM 수요 증가 감산 흑자전환",
                    "url": "https://t.test/1",
                    "published_at": "2026-05-16T09:00:00",
                },
            )
            db.insert(
                "news",
                {
                    "stock_code": "005930",
                    "title": "공급과잉 우려",
                    "summary": "재고 누적 가격 하락",
                    "cleaned_text": "공급과잉 재고누적 가격하락",
                    "url": "https://t.test/2",
                    "published_at": "2026-05-16T10:00:00",
                },
            )

        # 2) 일자별 적재 실행
        with SentimentEngine() as se:
            result = se.score_news_and_store("005930", "2026-05-16")

        self.assertEqual(result.news_count, 2)

        # 3) sentiment_scores 테이블 검증
        with DBControl(db_path=self.db_path) as db:
            row = db.fetch_one(
                "SELECT score, news_count, top_keywords FROM sentiment_scores "
                "WHERE stock_code = ? AND score_date = ?",
                ("005930", "2026-05-16"),
            )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["news_count"], 2)
        self.assertIsInstance(row["top_keywords"], str)
        kws = json.loads(row["top_keywords"])
        self.assertIsInstance(kws, list)
        self.assertGreater(len(kws), 0)

        # 4) 개별 news.sentiment_score 갱신 확인
        with DBControl(db_path=self.db_path) as db:
            scored = db.fetch_all(
                "SELECT sentiment_score FROM news WHERE stock_code = ?",
                ("005930",),
            )
        self.assertEqual(len(scored), 2)
        self.assertTrue(all(r["sentiment_score"] is not None for r in scored))

    def test_score_news_with_no_data_yields_zero(self) -> None:
        with DBControl(db_path=self.db_path) as db:
            db.upsert(
                "stocks",
                {"stock_code": "005930", "name": "삼성전자"},
                conflict_columns=["stock_code"],
            )
        with SentimentEngine() as se:
            result = se.score_news_and_store("005930", "2026-05-16")
        self.assertEqual(result.news_count, 0)
        self.assertEqual(result.score, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
