"""``NaverNewsCollector`` 단위 테스트 (T-010 ~ T-013).

외부 네트워크 호출은 모두 monkeypatch 로 대체한다.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from semi_senti.collector.news import NaverNewsCollector
from semi_senti.db import DBControl, init_database


def _make_settings_env(db_path: Path) -> None:
    """테스트용 환경 변수 강제 설정."""
    os.environ["SEMI_SENTI_SQLITE_PATH"] = str(db_path)
    os.environ["NAVER_CLIENT_ID"] = "DUMMY_ID"
    os.environ["NAVER_CLIENT_SECRET"] = "DUMMY_SECRET"
    os.environ["NEWS_CACHE_TTL_MINUTES"] = "60"


# 네이버 응답 형태를 모사한 fixture.
_FAKE_NAVER_RESPONSE = {
    "items": [
        {
            "title": "<b>HBM</b> 수요 폭증, &quot;역대급&quot; 주문",
            "description": "<b>SK하이닉스</b>는 ... 공급 확대 계획을 밝혔다.",
            "originallink": "https://example.test/news/1",
            "link": "https://example.test/news/1",
            "pubDate": "Mon, 26 May 2026 09:00:00 +0900",
        },
        {
            "title": "감산 효과 본격화",
            "description": "공급과잉 해소 신호가 ...",
            "originallink": "https://example.test/news/2",
            "link": "https://example.test/news/2",
            "pubDate": "Tue, 27 May 2026 10:30:00 +0900",
        },
        {
            # title 이 비어있는 항목은 skip 되어야 함.
            "title": "",
            "description": "<b>nothing</b>",
            "originallink": "https://example.test/news/3",
            "link": "https://example.test/news/3",
            "pubDate": "Wed, 28 May 2026 08:00:00 +0900",
        },
        {
            # URL 이 비어있는 항목도 skip.
            "title": "no url",
            "description": "x",
            "originallink": "",
            "link": "",
            "pubDate": "Thu, 29 May 2026 09:00:00 +0900",
        },
    ]
}


class TestNaverNewsCollector(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "news_test.db"
        _make_settings_env(self.db_path)
        init_database(db_path=self.db_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_collect_and_store_parses_and_filters(self) -> None:
        with patch.object(
            NaverNewsCollector,
            "_http_search",
            return_value=_FAKE_NAVER_RESPONSE["items"],
        ):
            with NaverNewsCollector() as nc:
                inserted = nc.collect_and_store(
                    stock_code="000660",
                    query="SK하이닉스",
                    stock_name="SK하이닉스",
                    market="KOSPI",
                    force=True,
                )

        self.assertEqual(inserted, 2)  # 빈 title / 빈 url 항목 2개는 제외

        with DBControl(db_path=self.db_path) as db:
            rows = db.fetch_all(
                "SELECT title, cleaned_text, url, published_at FROM news "
                "WHERE stock_code = ? ORDER BY published_at",
                ("000660",),
            )
            self.assertEqual(len(rows), 2)
            self.assertNotIn("<b>", rows[0]["title"])
            self.assertIn("HBM", rows[0]["title"])
            # pubDate 변환 검증 (YYYY-MM-DDTHH:MM:SS)
            self.assertRegex(rows[0]["published_at"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_dedup_on_repeated_call(self) -> None:
        """같은 URL 을 두 번 호출해도 row 가 1건만 남는다 (UNIQUE 제약)."""
        with patch.object(
            NaverNewsCollector,
            "_http_search",
            return_value=_FAKE_NAVER_RESPONSE["items"],
        ):
            with NaverNewsCollector() as nc:
                nc.collect_and_store(
                    stock_code="000660", query="x", stock_name="SK하이닉스", force=True
                )
                # 두 번째 호출도 force 로 우회.
                nc.collect_and_store(
                    stock_code="000660", query="x", stock_name="SK하이닉스", force=True
                )

        with DBControl(db_path=self.db_path) as db:
            rows = db.fetch_all(
                "SELECT url FROM news WHERE stock_code = ?", ("000660",)
            )
            urls = sorted(r["url"] for r in rows)
            self.assertEqual(urls, sorted(set(urls)))  # 중복 없음

    def test_cache_skip_when_fresh(self) -> None:
        """TTL 신선 시 API 호출 자체를 건너뛴다 (F-1.3.2)."""
        # 1차: force=True 로 적재
        with patch.object(
            NaverNewsCollector,
            "_http_search",
            return_value=_FAKE_NAVER_RESPONSE["items"],
        ):
            with NaverNewsCollector() as nc:
                nc.collect_and_store(
                    stock_code="000660", query="x", stock_name="SK하이닉스", force=True
                )

        # 2차: force=False → TTL 60분 내이므로 _http_search 호출되면 안 됨.
        with patch.object(NaverNewsCollector, "_http_search") as mocked:
            with NaverNewsCollector() as nc:
                inserted = nc.collect_and_store(
                    stock_code="000660", query="x", stock_name="SK하이닉스", force=False
                )
            mocked.assert_not_called()
        self.assertEqual(inserted, 0)

    def test_missing_credentials_raises(self) -> None:
        os.environ["NAVER_CLIENT_ID"] = ""
        os.environ["NAVER_CLIENT_SECRET"] = ""
        with NaverNewsCollector() as nc:
            from semi_senti.collector import CollectorError

            with self.assertRaises(CollectorError):
                # 내부 _http_search 가 자격 증명 검증을 수행.
                nc._http_search(query="x", display=1, start=1, sort="date")
        # 복원
        os.environ["NAVER_CLIENT_ID"] = "DUMMY_ID"
        os.environ["NAVER_CLIENT_SECRET"] = "DUMMY_SECRET"


if __name__ == "__main__":
    unittest.main(verbosity=2)
