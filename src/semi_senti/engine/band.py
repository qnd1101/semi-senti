"""펀더멘털 적정 가치 밴드 산출 (T-023, F-3.1).

> "재무 지표(PER·PBR·EPS·영업이익)를 기반으로 종목별 적정 가치 밴드(상단·하단)
>  를 산출한다." — PRD §F-3.1.1

산출 로직 (v2 — 주가 분위 우선)
---------------------------------
1. **1순위 — 주가 분위 방식**
   - 최근 N일(기본 250 거래일) close_price 의 20/80 분위.
   - 이상치 방어: 현재가의 [30%, 300%] 범위 밖 데이터는 제외 후 분위 산출.
2. **보조 — PER × EPS 방식** (분위 방식 결과 교정에만 사용)
   - ``band_mid = avg(PER 최근 N건) × 최신 EPS``
   - PER·EPS 기반 mid 가 현재가의 [0.5, 2.0] 범위 안에 들 때만 사용.
   - 오염·고PER 방어: 범위 밖이면 분위 결과를 그대로 사용.
3. **폴백** — close 데이터가 3개 미만이면 unavailable.
4. **margin** 은 ``Settings.band_margin`` (기본 0.15) 으로 통일.

본 모듈은 stateless 하게 동작하며 DB 의 ``financials`` 테이블만 읽는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)

# 이상치 방어 비율 (현재가 대비)
_CLOSE_OUTLIER_LOW = 0.30   # 현재가의 30% 미만은 이상치로 제외
_CLOSE_OUTLIER_HIGH = 3.00  # 현재가의 300% 초과는 이상치로 제외

# PER×EPS 방식이 현재가 대비 이 범위 안에 있을 때만 보조 채택
_PER_EPS_BAND_LOW_RATIO = 0.5
_PER_EPS_BAND_HIGH_RATIO = 2.0

# PER 이상치 방어 (반도체 정상 범위 고려: 0 초과 ~ 150 이하)
_PER_MIN = 0.1
_PER_MAX = 150.0


@dataclass
class Band:
    """펀더멘털 밴드 결과."""

    stock_code: str
    band_low: Optional[float]
    band_high: Optional[float]
    band_mid: Optional[float]
    method: str                 # 'price_quantile' | 'price_quantile+per_eps' | 'unavailable'
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
        """주어진 종목의 펀더멘털 밴드를 산출.

        1순위: 최근 lookback_days 일 close_price 의 20/80 분위 (이상치 필터 적용).
        보조: PER×EPS 방식이 현재가의 [0.5, 2.0] 배 범위 안에 있으면 low/high 교정.
        """
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")
        lookback = int(lookback_days or self._settings.band_lookback_days)
        margin = float(self._settings.band_margin)

        rows = self.db().fetch_all(
            "SELECT record_date, close_price, per, eps "
            "FROM financials WHERE stock_code = %s "
            "ORDER BY record_date DESC LIMIT %s",
            (stock_code, lookback),
        )

        # --- 현재가 (최신 close_price)
        current_price: Optional[float] = next(
            (float(r["close_price"]) for r in rows if r.get("close_price") is not None),
            None,
        )

        # ---- 1순위: 주가 분위 방식 ------------------------------------------
        all_close: List[float] = [
            float(r["close_price"]) for r in rows if r.get("close_price") is not None
        ]

        # 이상치 필터: 현재가 기준 [30%, 300%] 범위 밖 제거
        if current_price is not None and current_price > 0:
            low_bound = current_price * _CLOSE_OUTLIER_LOW
            high_bound = current_price * _CLOSE_OUTLIER_HIGH
            filtered_close = [c for c in all_close if low_bound <= c <= high_bound]
        else:
            filtered_close = all_close

        # 필터 후 데이터가 너무 적으면 필터 해제
        if len(filtered_close) < 5 and len(all_close) >= 5:
            _LOGGER.warning(
                "이상치 필터 후 데이터 부족(%d개) -> 필터 해제: stock=%s",
                len(filtered_close), stock_code,
            )
            filtered_close = all_close

        if len(filtered_close) >= 3:
            sorted_close = sorted(filtered_close)
            q_low = self._quantile(sorted_close, 0.20)
            q_high = self._quantile(sorted_close, 0.80)
            q_mid = (q_low + q_high) / 2

            _LOGGER.debug(
                "주가 분위 밴드 [%s]: low=%.0f, high=%.0f (n=%d, 현재가=%.0f)",
                stock_code, q_low, q_high, len(filtered_close),
                current_price if current_price else 0,
            )

            # ---- 보조: PER×EPS 방식 (현재가 [0.5, 2.0] 범위 안일 때만 채택) ----
            if current_price is not None and current_price > 0:
                per_mid = self._per_eps_mid(rows, current_price)
                if per_mid is not None:
                    ratio = per_mid / current_price
                    if _PER_EPS_BAND_LOW_RATIO <= ratio <= _PER_EPS_BAND_HIGH_RATIO:
                        # 두 방식 중간값 채택으로 안정화
                        blend_mid = (q_mid + per_mid) / 2
                        band_low = blend_mid * (1 - margin)
                        band_high = blend_mid * (1 + margin)
                        _LOGGER.debug(
                            "PER×EPS 보조 채택 [%s]: per_mid=%.0f, blend_mid=%.0f, ratio=%.2f",
                            stock_code, per_mid, blend_mid, ratio,
                        )
                        return Band(
                            stock_code=stock_code,
                            band_mid=blend_mid,
                            band_low=band_low,
                            band_high=band_high,
                            method="price_quantile+per_eps",
                            sample_size=len(filtered_close),
                        )
                    else:
                        _LOGGER.debug(
                            "PER×EPS 무효 [%s]: per_mid=%.0f, 현재가=%.0f, ratio=%.2f (범위 밖)",
                            stock_code, per_mid, current_price, ratio,
                        )

            return Band(
                stock_code=stock_code,
                band_mid=q_mid,
                band_low=q_low,
                band_high=q_high,
                method="price_quantile",
                sample_size=len(filtered_close),
            )

        # ---- 폴백: 데이터 부족 -----------------------------------------------
        _LOGGER.warning("밴드 산출 불가 (데이터 부족): stock=%s, rows=%d", stock_code, len(rows))
        return Band(
            stock_code=stock_code,
            band_mid=None,
            band_low=None,
            band_high=None,
            method="unavailable",
            sample_size=len(rows),
        )

    # ------------------------------------------------------------------ helpers
    def _per_eps_mid(self, rows: List[dict], current_price: float) -> Optional[float]:
        """PER×EPS 방식의 band_mid 를 산출. 오염 PER(범위 밖) 필터 적용."""
        per_values: List[float] = [
            float(r["per"]) for r in rows
            if r.get("per") is not None and _PER_MIN <= float(r["per"]) <= _PER_MAX
        ]
        latest_eps: Optional[float] = next(
            (float(r["eps"]) for r in rows if r.get("eps") is not None and float(r["eps"]) > 0),
            None,
        )
        if not per_values or latest_eps is None:
            return None
        avg_per = sum(per_values) / len(per_values)
        return avg_per * latest_eps

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
