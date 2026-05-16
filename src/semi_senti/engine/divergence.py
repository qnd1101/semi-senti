"""다이버전스(괴리) 탐지 (T-026, T-027, F-2.3).

> "주가 추세와 감성 지수 추세가 반대로 움직이는 괴리 현상을 실시간으로 탐지한다."
>  — PRD §F-2.3.1

탐지 규칙
---------
- N일 윈도우의 첫값/끝값 비교로 추세 부호와 변화율(%, pt) 산출.
- **강세(Bullish)**: 주가 하락 + 감성 상승 → 'BULLISH_OPPORTUNITY' (황색 ◆)
- **약세(Bearish)**: 주가 상승 + 감성 하락 → 'BEARISH_CAUTION' (보라색 ◆)
- 부호가 같거나 변화가 임계값 미만이면 ``'NONE'``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)

DivergenceType = str  # 'BULLISH_OPPORTUNITY' | 'BEARISH_CAUTION' | 'NONE'


@dataclass
class DivergenceResult:
    """다이버전스 탐지 결과."""

    stock_code: str
    divergence_type: DivergenceType
    price_change_pct: float
    sentiment_change_pt: float
    window_days: int
    note: str

    @property
    def detected(self) -> bool:
        return self.divergence_type != "NONE"


class DivergenceDetector:
    """주가 N일 추세 vs 감성 지수 N일 추세 비교."""

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

    def __enter__(self) -> "DivergenceDetector":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ core
    def detect(self, stock_code: str, window_days: Optional[int] = None) -> DivergenceResult:
        """DB 에서 시계열을 읽어 다이버전스 여부 판단."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")
        n = int(window_days or self._settings.divergence_window_days)
        if n < 2:
            raise ValueError("window_days 는 2 이상이어야 합니다.")

        price_series = self._load_price_series(stock_code, n)
        sentiment_series = self._load_sentiment_series(stock_code, n)
        return self._evaluate(
            stock_code=stock_code,
            price_series=price_series,
            sentiment_series=sentiment_series,
            window_days=n,
        )

    # ------------------------------------------------------------------ pure logic (T-027)
    def _evaluate(
        self,
        *,
        stock_code: str,
        price_series: Sequence[float],
        sentiment_series: Sequence[float],
        window_days: int,
    ) -> DivergenceResult:
        """입력 시계열로부터 다이버전스를 판정. 단위 테스트하기 쉬운 순수 함수."""
        if len(price_series) < 2 or len(sentiment_series) < 2:
            return DivergenceResult(
                stock_code=stock_code,
                divergence_type="NONE",
                price_change_pct=0.0,
                sentiment_change_pt=0.0,
                window_days=window_days,
                note="데이터 부족",
            )

        price_change = self._pct_change(price_series[0], price_series[-1])
        sentiment_change = float(sentiment_series[-1] - sentiment_series[0])

        p_th = float(self._settings.divergence_price_threshold)
        s_th = float(self._settings.divergence_sentiment_threshold)

        # 변화 절대값이 임계값 미만이면 탐지하지 않음.
        if abs(price_change) < p_th or abs(sentiment_change) < s_th:
            return DivergenceResult(
                stock_code=stock_code,
                divergence_type="NONE",
                price_change_pct=price_change,
                sentiment_change_pt=sentiment_change,
                window_days=window_days,
                note=(
                    f"변화 미달: price={price_change:.2f}%(<{p_th}), "
                    f"sentiment={sentiment_change:.2f}pt(<{s_th})"
                ),
            )

        # 부호 비교 (반대 방향일 때만 다이버전스).
        if price_change < 0 and sentiment_change > 0:
            return DivergenceResult(
                stock_code=stock_code,
                divergence_type="BULLISH_OPPORTUNITY",
                price_change_pct=price_change,
                sentiment_change_pt=sentiment_change,
                window_days=window_days,
                note=f"강세 다이버전스: 주가 {price_change:.2f}% / 감성 +{sentiment_change:.2f}pt",
            )
        if price_change > 0 and sentiment_change < 0:
            return DivergenceResult(
                stock_code=stock_code,
                divergence_type="BEARISH_CAUTION",
                price_change_pct=price_change,
                sentiment_change_pt=sentiment_change,
                window_days=window_days,
                note=f"약세 다이버전스: 주가 +{price_change:.2f}% / 감성 {sentiment_change:.2f}pt",
            )

        return DivergenceResult(
            stock_code=stock_code,
            divergence_type="NONE",
            price_change_pct=price_change,
            sentiment_change_pt=sentiment_change,
            window_days=window_days,
            note="같은 방향 - 다이버전스 아님",
        )

    @staticmethod
    def _pct_change(first: float, last: float) -> float:
        if first is None or last is None or first == 0:
            return 0.0
        return (float(last) - float(first)) / float(first) * 100.0

    # ------------------------------------------------------------------ data loaders
    def _load_price_series(self, stock_code: str, n: int) -> List[float]:
        rows = self.db().fetch_all(
            "SELECT close_price FROM financials WHERE stock_code = ? "
            "AND close_price IS NOT NULL ORDER BY record_date DESC LIMIT ?",
            (stock_code, n),
        )
        # 최신 → 과거 순으로 가져왔으니 뒤집어 과거→최신 순서로 반환.
        return [float(r["close_price"]) for r in reversed(rows)]

    def _load_sentiment_series(self, stock_code: str, n: int) -> List[float]:
        rows = self.db().fetch_all(
            "SELECT score FROM sentiment_scores WHERE stock_code = ? "
            "ORDER BY score_date DESC LIMIT ?",
            (stock_code, n),
        )
        return [float(r["score"]) for r in reversed(rows)]
