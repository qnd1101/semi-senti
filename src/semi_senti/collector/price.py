"""pykrx 일별 주가 수집 모듈 (F-1.1.2).

PRD v1.2: yfinance → pykrx 전환
- pykrx 는 API 키 불필요, KRX·네이버 기반 무료 소스
- 무료 pykrx 기준 약 3,000거래일(2014년 이후) 제공
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseCollector, CollectorError
from .market_data import (
    fetch_all_daily_history,
    fetch_recent_daily,
    to_yahoo_symbol,
)
from .normalizer import DataNormalizer

_LOGGER = logging.getLogger(__name__)

_MIN_FULL_HISTORY_ROWS = 500


class PriceCollector(BaseCollector):
    """pykrx 일별 주가 수집기."""

    source_name = "pykrx"

    @staticmethod
    def to_yahoo_symbol(stock_code: str, market: str = "KOSPI") -> str:
        """하위 호환 — market_data 위임."""
        return to_yahoo_symbol(stock_code, market)

    def _upsert_price_rows(
        self,
        stock_code: str,
        history: List[Dict[str, Any]],
    ) -> int:
        affected = 0
        for raw in history:
            record_date = raw.get("record_date") or raw.get("time")
            if not record_date:
                continue
            record = DataNormalizer.normalize_financial_record(
                stock_code=stock_code,
                record_date=str(record_date)[:10],
                raw={
                    "open": raw.get("open"),
                    "high": raw.get("high"),
                    "low": raw.get("low"),
                    "close": raw.get("close"),
                    "volume": raw.get("volume"),
                },
            )
            self.db().upsert(
                "financials",
                record,
                conflict_columns=["stock_code", "record_date"],
                update_columns=[
                    "open_price",
                    "high_price",
                    "low_price",
                    "close_price",
                    "volume",
                    "currency",
                    "updated_at",
                ],
            )
            affected += 1
        return affected

    def _fetch_history(
        self,
        stock_code: str,
        *,
        market: str = "KOSPI",
        days: int = 31,
        full: bool = False,
    ) -> List[Dict[str, Any]]:
        from_date = getattr(self.settings, "pykrx_date_from", "20140101")
        if full:
            rows = fetch_all_daily_history(stock_code, market=market, from_date=from_date)
        else:
            rows = fetch_recent_daily(stock_code, market=market, days=days)
        return [
            {
                "record_date": r["time"],
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "close": r.get("close"),
                "volume": r.get("volume"),
            }
            for r in rows
        ]

    def count_price_rows(self, stock_code: str) -> int:
        row = self.db().fetch_one(
            "SELECT COUNT(*) AS cnt FROM financials "
            "WHERE stock_code = %s AND close_price IS NOT NULL",
            (stock_code,),
        )
        return int((row or {}).get("cnt") or 0)

    def collect_full_history_and_store(
        self,
        stock_code: str,
        *,
        market: str = "KOSPI",
        stock_name: Optional[str] = None,
        force: bool = False,
    ) -> int:
        """가능한 전체 일봉을 ``financials`` 에 적재."""
        if not stock_code:
            raise CollectorError("collect_full_history_and_store: stock_code 필수")

        self.ensure_stock(stock_code=stock_code, name=stock_name, market=market)

        if not force and self.count_price_rows(stock_code) >= _MIN_FULL_HISTORY_ROWS:
            _LOGGER.info("전체 주가 이미 적재됨 → skip: %s", stock_code)
            return 0

        def _api_call() -> List[Dict[str, Any]]:
            return self._fetch_history(stock_code, market=market, full=True)

        def _fallback() -> List[Dict[str, Any]]:
            rows = self.db().fetch_all(
                "SELECT record_date, open_price AS open, high_price AS high, "
                "low_price AS low, close_price AS close, volume FROM financials "
                "WHERE stock_code = %s AND close_price IS NOT NULL ORDER BY record_date",
                (stock_code,),
            )
            if not rows:
                raise CollectorError(f"폴백 캐시 없음: {stock_code}")
            return [
                {
                    "record_date": r["record_date"],
                    "open": r.get("open"),
                    "high": r.get("high"),
                    "low": r.get("low"),
                    "close": r.get("close"),
                    "volume": r.get("volume"),
                }
                for r in rows
            ]

        history = self._safe_call_api(
            _api_call,
            fallback_callable=_fallback,
            operation_name=f"pykrx-full({stock_code})",
        )
        affected = self._upsert_price_rows(stock_code, history)
        _LOGGER.info("pykrx 전체 적재: stock=%s rows=%d", stock_code, affected)
        return affected

    def collect_and_store(
        self,
        stock_code: str,
        *,
        market: str = "KOSPI",
        stock_name: Optional[str] = None,
        period: Optional[str] = None,
        interval: Optional[str] = None,
        force: bool = False,
    ) -> int:
        """최근 일봉 갱신 (폴링용). ``period``/``interval`` 은 하위 호환용 무시."""
        del period, interval

        if not stock_code:
            raise CollectorError("collect_and_store: stock_code 는 필수입니다.")

        self.ensure_stock(stock_code=stock_code, name=stock_name, market=market)

        if not force and self.is_cache_fresh(stock_code):
            _LOGGER.info("pykrx 캐시 신선 → API 호출 생략: %s", stock_code)
            return 0

        def _api_call() -> List[Dict[str, Any]]:
            return self._fetch_history(stock_code, market=market, days=31)

        def _fallback() -> List[Dict[str, Any]]:
            rows = self.db().fetch_all(
                "SELECT record_date, open_price AS open, high_price AS high, "
                "low_price AS low, close_price AS close, volume FROM financials "
                "WHERE stock_code = %s ORDER BY record_date DESC LIMIT 30",
                (stock_code,),
            )
            if not rows:
                raise CollectorError(f"폴백 캐시 없음: {stock_code}")
            return list(reversed(rows))

        history = self._safe_call_api(
            _api_call,
            fallback_callable=_fallback,
            operation_name=f"pykrx({stock_code})",
        )
        affected = self._upsert_price_rows(stock_code, history)
        _LOGGER.info("pykrx 적재 완료: stock=%s, rows=%d", stock_code, affected)
        return affected

    def is_cache_fresh(self, stock_code: str) -> bool:
        row = self.db().fetch_one(
            "SELECT updated_at FROM financials "
            "WHERE stock_code = %s AND close_price IS NOT NULL "
            "ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        if not row:
            return False
        ttl = timedelta(minutes=self.settings.price_cache_ttl_minutes)
        return self._is_cache_fresh(row.get("updated_at"), ttl)

    def fetch_db_candles(self, stock_code: str) -> List[Dict[str, Any]]:
        """DB 에 적재된 일봉 (차트용)."""
        rows = self.db().fetch_all(
            "SELECT record_date AS time, open_price AS open, high_price AS high, "
            "low_price AS low, close_price AS close, volume "
            "FROM financials WHERE stock_code = %s AND close_price IS NOT NULL "
            "ORDER BY record_date ASC",
            (stock_code,),
        )
        out: List[Dict[str, Any]] = []
        for r in rows:
            t = str(r.get("time") or "")[:10]
            close = r.get("close")
            if not t or close is None:
                continue
            out.append(
                {
                    "time": t,
                    "open": float(r.get("open") or close),
                    "high": float(r.get("high") or close),
                    "low": float(r.get("low") or close),
                    "close": float(close),
                    "volume": int(r.get("volume") or 0),
                }
            )
        return out
