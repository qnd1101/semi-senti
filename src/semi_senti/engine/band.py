"""펀더멘털 적정 가치 밴드 산출 (T-023, F-3.1).

> "재무 지표(PER·PBR·EPS·영업이익)를 기반으로 종목별 적정 가치 밴드(상단·하단)
>  를 산출한다." — PRD §F-3.1.1

산출 로직 (Phase 2 초안)
-----------------------
1. **1순위 — PER × EPS 방식**
   - ``band_mid = avg(PER 과거 N건) × 최신 EPS``
   - ``band_low/high = band_mid × (1 ∓ margin)``
2. **폴백 — 주가 분위 방식** (PER/EPS 부재 시)
   - 최근 N일 종가의 20/80 분위 사용.
3. **margin** 은 ``Settings.band_margin`` (기본 0.15) 으로 통일.

본 모듈은 stateless 하게 동작하며 DB 의 ``financials`` 테이블만 읽는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)


@dataclass
class Band:
    """펀더멘털 밴드 결과."""

    stock_code: str
    band_low: Optional[float]
    band_high: Optional[float]
    band_mid: Optional[float]
    method: str                 # 'per_eps' | 'price_quantile' | 'unavailable'
    sample_size: int = 0

    @property
    def is_valid(self) -> bool:
        return self.band_low is not None and self.band_high is not None


class FundamentalBand:
    """``financials`` 테이블에서 적정 가치 밴드를 계산."""

    def __init__(
        self,
        db: Optional[DBControl] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None

    # ------------------------------------------------------------------ life
    def db(self) -> DBControl:
        if self._db is None:
            self._db = DBControl(db_path=self._settings.sqlite_path)
            self._db.connect()
        else:
            self._db.connect()
        return self._db

    def close(self) -> None:
        if self._owns_db and self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self) -> "FundamentalBand":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ core
    def compute(self, stock_code: str, lookback_days: Optional[int] = None) -> Band:
        """주어진 종목의 펀더멘털 밴드를 산출."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")
        lookback = int(lookback_days or self._settings.band_lookback_days)
        margin = float(self._settings.band_margin)

        rows = self.db().fetch_all(
            "SELECT record_date, close_price, per, eps "
            "FROM financials WHERE stock_code = ? "
            "ORDER BY record_date DESC LIMIT ?",
            (stock_code, lookback),
        )

        # 1) 1순위: PER × EPS
        per_values: List[float] = [r["per"] for r in rows if r.get("per") is not None]
        latest_eps: Optional[float] = next(
            (r["eps"] for r in rows if r.get("eps") is not None), None
        )
        if per_values and latest_eps is not None and latest_eps > 0:
            avg_per = sum(per_values) / len(per_values)
            band_mid = avg_per * latest_eps
            return Band(
                stock_code=stock_code,
                band_mid=band_mid,
                band_low=band_mid * (1 - margin),
                band_high=band_mid * (1 + margin),
                method="per_eps",
                sample_size=len(per_values),
            )

        # 2) 폴백: 주가 분위
        close_values: List[float] = [
            r["close_price"] for r in rows if r.get("close_price") is not None
        ]
        if len(close_values) >= 3:
            sorted_close = sorted(close_values)
            band_low = self._quantile(sorted_close, 0.20)
            band_high = self._quantile(sorted_close, 0.80)
            band_mid = (band_low + band_high) / 2
            return Band(
                stock_code=stock_code,
                band_mid=band_mid,
                band_low=band_low,
                band_high=band_high,
                method="price_quantile",
                sample_size=len(close_values),
            )

        # 3) 데이터 부족
        _LOGGER.warning("밴드 산출 불가 (데이터 부족): stock=%s, rows=%d", stock_code, len(rows))
        return Band(
            stock_code=stock_code,
            band_mid=None,
            band_low=None,
            band_high=None,
            method="unavailable",
            sample_size=len(rows),
        )

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _quantile(sorted_values: List[float], q: float) -> float:
        """간단한 선형 보간 분위수. numpy 의존성 회피."""
        if not sorted_values:
            raise ValueError("빈 시퀀스의 분위수는 정의되지 않습니다.")
        if len(sorted_values) == 1:
            return float(sorted_values[0])
        q = max(0.0, min(1.0, q))
        pos = q * (len(sorted_values) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(sorted_values) - 1)
        frac = pos - lo
        return float(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac)
