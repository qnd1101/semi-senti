"""yfinance 일별 주가 수집 모듈 (T-007, T-009).

> "yfinance API를 통해 일별 종가·고가·저가·거래량 주가 데이터를 수집한다."
>  — PRD F-1.1.2

설계
----
- 한국 종목 코드는 yfinance 에서 ``005930.KS``(KOSPI) / ``035720.KQ``(KOSDAQ)
  형태의 suffix 가 필요하다. 본 모듈은 ``market`` 인자로 KOSPI/KOSDAQ 을 받아
  자동 매핑한다.
- yfinance 가 설치되지 않은 환경에서도 import 가 깨지지 않도록 lazy import.
- 캐시 정책: TTL 내 데이터가 존재하면 API 호출을 생략 (F-1.3.2).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Mapping, Optional

from .base import BaseCollector, CollectorError
from .normalizer import DataNormalizer

_LOGGER = logging.getLogger(__name__)

_MARKET_SUFFIX = {
    "KOSPI": ".KS",
    "KOSDAQ": ".KQ",
    "KS": ".KS",
    "KQ": ".KQ",
}


class PriceCollector(BaseCollector):
    """yfinance 일별 주가 수집기."""

    source_name = "yfinance"

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def to_yahoo_symbol(stock_code: str, market: str = "KOSPI") -> str:
        """KRX 6자리 코드 → 야후 심볼 ('005930' + KOSPI → '005930.KS')."""
        if not stock_code:
            raise CollectorError("to_yahoo_symbol: stock_code 는 필수입니다.")
        if "." in stock_code:
            # 이미 suffix 가 포함된 경우는 그대로 사용.
            return stock_code
        suffix = _MARKET_SUFFIX.get((market or "KOSPI").upper())
        if not suffix:
            raise CollectorError(
                f"지원하지 않는 market: {market!r} (KOSPI/KOSDAQ 만 허용)"
            )
        return f"{stock_code}{suffix}"

    def _fetch_history(
        self,
        symbol: str,
        period: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """yfinance 호출. 반환은 list of dict (DataFrame 의존성을 격리)."""
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CollectorError(
                "'yfinance' 패키지가 필요합니다. `pip install -r requirements.txt`."
            ) from exc

        period = period or self.settings.yfinance_default_period
        interval = interval or self.settings.yfinance_default_interval

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:  # yfinance 는 다양한 예외 타입을 던짐.
            raise CollectorError(f"yfinance 호출 실패 ({symbol}): {exc}") from exc

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for ts, row in df.iterrows():
            # ts: pandas.Timestamp (tz-aware 가능)
            try:
                date_str = ts.strftime("%Y-%m-%d")
            except AttributeError:
                date_str = str(ts)[:10]
            rows.append(
                {
                    "record_date": date_str,
                    "open": float(row.get("Open")) if row.get("Open") is not None else None,
                    "high": float(row.get("High")) if row.get("High") is not None else None,
                    "low": float(row.get("Low")) if row.get("Low") is not None else None,
                    "close": float(row.get("Close")) if row.get("Close") is not None else None,
                    "volume": int(row.get("Volume")) if row.get("Volume") is not None else None,
                }
            )
        return rows

    # ------------------------------------------------------------------ public
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
        """주가 데이터를 수집해 ``financials`` 테이블에 UPSERT.

        Parameters
        ----------
        force:
            True 시 TTL 무시하고 강제 갱신.

        Returns
        -------
        int
            영향을 받은 row 개수 (수집 + 적재).
        """
        if not stock_code:
            raise CollectorError("collect_and_store: stock_code 는 필수입니다.")

        self.ensure_stock(stock_code=stock_code, name=stock_name, market=market)

        # F-1.3.2 TTL 캐시 체크.
        if not force and self.is_cache_fresh(stock_code):
            _LOGGER.info("yfinance 캐시 신선 → API 호출 생략: %s", stock_code)
            return 0

        symbol = self.to_yahoo_symbol(stock_code, market)

        def _api_call() -> List[Dict[str, Any]]:
            return self._fetch_history(symbol, period=period, interval=interval)

        def _fallback() -> List[Dict[str, Any]]:
            # 폴백: 캐시된 가장 최근 N건을 반환 (별도 적재는 불필요).
            rows = self.db().fetch_all(
                "SELECT record_date, open_price AS open, high_price AS high, "
                "low_price AS low, close_price AS close, volume FROM financials "
                "WHERE stock_code = ? ORDER BY record_date DESC LIMIT 30",
                (stock_code,),
            )
            if not rows:
                raise CollectorError(f"폴백 캐시 없음: {stock_code}")
            return rows

        history = self._safe_call_api(
            _api_call,
            fallback_callable=_fallback,
            operation_name=f"yfinance({symbol})",
        )

        affected = 0
        for raw in history:
            record = DataNormalizer.normalize_financial_record(
                stock_code=stock_code,
                record_date=raw["record_date"],
                raw=raw,
            )
            # 재무 컬럼(revenue 등)은 이 단계에서 모름 → None 유지(UPSERT 시 보존되도록 update 컬럼 제한).
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

        _LOGGER.info("yfinance 적재 완료: stock=%s, rows=%d", stock_code, affected)
        return affected

    # ------------------------------------------------------------------ cache check
    def is_cache_fresh(self, stock_code: str) -> bool:
        row = self.db().fetch_one(
            "SELECT updated_at FROM financials "
            "WHERE stock_code = ? AND close_price IS NOT NULL "
            "ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        if not row:
            return False
        ttl = timedelta(minutes=self.settings.price_cache_ttl_minutes)
        return self._is_cache_fresh(row.get("updated_at"), ttl)
