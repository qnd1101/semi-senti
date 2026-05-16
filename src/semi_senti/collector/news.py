"""네이버 뉴스 검색 API 수집 모듈 (T-010, T-011, T-013).

> "네이버 뉴스 검색 API를 통해 종목명 키워드로 실시간 기사를 수집한다."
>  — PRD F-1.2.1
>
> "API 일일 호출 쿼터(DART·네이버) 초과를 방지하기 위해 캐시 유효 시간(TTL)
>  을 설정한다." — PRD F-1.3.2

설계
----
- 네이버 응답의 ``title`` / ``description`` 은 ``<b>...</b>`` 강조 태그 포함
  HTML 이므로 ``TextCleaner`` 로 정제 후 ``cleaned_text`` 컬럼에 저장한다.
- ``pubDate`` 는 "Mon, 26 May 2026 09:00:00 +0900" 형식. ISO 로 변환.
- 중복은 ``UNIQUE(stock_code, url)`` 제약으로 차단 (UPSERT 사용 시 충돌만 무시).
- TTL 정책 (F-1.3.2):
  ``stock_code`` 별 가장 최근 ``collected_at`` 이 TTL 내면 API 호출 자체를 생략.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Mapping, Optional

from .base import BaseCollector, CollectorError
from .cleaner import TextCleaner

_LOGGER = logging.getLogger(__name__)


class NaverNewsCollector(BaseCollector):
    """네이버 뉴스 검색 API 수집기."""

    source_name = "naver_news"

    def __init__(self, *args, cleaner: Optional[TextCleaner] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._cleaner = cleaner or TextCleaner()

    # ------------------------------------------------------------------ helpers
    def _require_credentials(self) -> Dict[str, str]:
        client_id = self.settings.naver_client_id
        client_secret = self.settings.naver_client_secret
        if not client_id or not client_secret:
            raise CollectorError(
                "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다."
            )
        return {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    @staticmethod
    def _parse_pub_date(raw: Optional[str]) -> str:
        """네이버 pubDate(RFC 822) → ISO 8601 ('YYYY-MM-DDTHH:MM:SS')."""
        if not raw:
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        try:
            dt = parsedate_to_datetime(raw)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    def _http_search(
        self,
        query: str,
        display: int,
        start: int,
        sort: str,
    ) -> List[Dict[str, Any]]:
        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CollectorError(
                "'requests' 패키지가 필요합니다. `pip install -r requirements.txt`."
            ) from exc

        headers = self._require_credentials()
        params = {
            "query": query,
            "display": max(1, min(int(display), 100)),
            "start": max(1, int(start)),
            "sort": sort if sort in ("date", "sim") else "date",
        }
        try:
            resp = requests.get(
                self.settings.naver_news_base_url,
                params=params,
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CollectorError(f"Naver 뉴스 API HTTP 실패: {exc}") from exc
        try:
            payload = resp.json()
        except ValueError as exc:
            raise CollectorError(f"Naver 뉴스 JSON 파싱 실패: {exc}") from exc

        items = payload.get("items")
        if not isinstance(items, list):
            return []
        return items

    # ------------------------------------------------------------------ public
    def collect_and_store(
        self,
        stock_code: str,
        query: str,
        *,
        stock_name: Optional[str] = None,
        market: Optional[str] = None,
        display: Optional[int] = None,
        start: int = 1,
        sort: Optional[str] = None,
        force: bool = False,
    ) -> int:
        """뉴스 검색 + 정제 + ``news`` 테이블 적재.

        Returns
        -------
        int
            실제로 새로 적재된 row 개수.

        Notes
        -----
        - 동일 ``(stock_code, url)`` 가 이미 있으면 UPSERT 가 충돌 무시되어
          0 으로 카운트되지 않을 수 있다 (총 시도 row 수와 다름).
        - TTL 캐시 신선 시 API 호출 자체를 생략하고 0 을 반환한다.
        """
        if not stock_code or not query:
            raise CollectorError("collect_and_store: stock_code/query 는 필수입니다.")

        self.ensure_stock(stock_code=stock_code, name=stock_name, market=market)

        # F-1.3.2 TTL 기반 중복 호출 방지.
        if not force and self.is_cache_fresh(stock_code):
            _LOGGER.info("네이버 뉴스 캐시 신선 → API 호출 생략: %s", stock_code)
            return 0

        display = display or self.settings.naver_news_display
        sort = sort or self.settings.naver_news_sort

        def _api_call() -> List[Dict[str, Any]]:
            return self._http_search(query=query, display=display, start=start, sort=sort)

        def _fallback() -> List[Dict[str, Any]]:
            # 폴백: 캐시된 뉴스를 그대로 반환 (재적재는 하지 않음).
            rows = self.db().fetch_all(
                "SELECT title, summary, cleaned_text, url, published_at "
                "FROM news WHERE stock_code = ? "
                "ORDER BY published_at DESC LIMIT 20",
                (stock_code,),
            )
            if not rows:
                raise CollectorError(f"폴백 캐시 없음: {stock_code}")
            return []  # 폴백 시 새로 적재할 데이터는 없음.

        items = self._safe_call_api(
            _api_call,
            fallback_callable=_fallback,
            operation_name=f"NaverNews({stock_code})",
        )

        new_inserts = 0
        for item in items:
            try:
                title_clean = self._cleaner.clean(item.get("title"))
                summary_clean = self._cleaner.clean(item.get("description"))
                if not title_clean:
                    # 본문 가치 없는 항목은 건너뜀.
                    continue
                url = (item.get("originallink") or item.get("link") or "").strip()
                if not url:
                    # URL 이 없으면 (stock_code, NULL) 충돌 방지를 위해 published_at 으로 임시 키 부여 못 함.
                    # 정책: URL 부재 시 적재 스킵.
                    continue
                record = {
                    "stock_code": stock_code,
                    "title": title_clean[:500],
                    "summary": summary_clean[:1000] or None,
                    "cleaned_text": summary_clean or None,
                    "source": self.source_name,
                    "url": url,
                    "published_at": self._parse_pub_date(item.get("pubDate")),
                }
                affected = self.db().upsert(
                    "news",
                    record,
                    conflict_columns=["stock_code", "url"],
                    # 충돌 시 갱신 컬럼은 정제 결과만 → 원본 published_at/collected_at 보존.
                    update_columns=["title", "summary", "cleaned_text"],
                )
                if affected > 0:
                    new_inserts += 1
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("뉴스 적재 중 일부 실패 (skip): %s", exc)
                continue

        _LOGGER.info("네이버 뉴스 적재 완료: stock=%s, new=%d / total=%d",
                     stock_code, new_inserts, len(items))
        return new_inserts

    # ------------------------------------------------------------------ cache check (F-1.3.2)
    def is_cache_fresh(self, stock_code: str) -> bool:
        row = self.db().fetch_one(
            "SELECT collected_at FROM news WHERE stock_code = ? "
            "ORDER BY collected_at DESC LIMIT 1",
            (stock_code,),
        )
        if not row:
            return False
        ttl = timedelta(minutes=self.settings.news_cache_ttl_minutes)
        return self._is_cache_fresh(row.get("collected_at"), ttl)
