"""매매 시그널 산출 및 적재 (T-022, T-024, T-025).

> "IF 현재가 < Band_Low AND Sentiment Score < -70 → BUY ...
>  ELSE IF 현재가 > Band_High AND Sentiment Score > +70 → SELL ...
>  ELSE → HOLD" — PRD §F-3.2 시그널 산출 로직

본 모듈은 다음 두 가지 입력을 받아 ``signals`` 테이블에 매매 시그널을 적재한다.

- ``FundamentalBand.compute(stock_code)`` → 적정 밴드(상단·하단)
- ``SentimentEngine.get_latest_score(stock_code)`` → 최신 감성 점수
- ``financials`` 테이블의 최신 ``close_price`` → 현재가
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import Settings, get_settings
from ..db import DBControl
from .band import Band, FundamentalBand
from .sentiment import SentimentEngine

_LOGGER = logging.getLogger(__name__)

SignalType = str  # 'BUY' | 'SELL' | 'HOLD'


@dataclass
class SignalDecision:
    """시그널 산출 결과."""

    stock_code: str
    signal_type: SignalType
    price: Optional[float]
    band_low: Optional[float]
    band_high: Optional[float]
    sentiment_score: Optional[float]
    rationale: str
    signaled_at: str

    def to_db_row(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "signal_type": self.signal_type,
            "price": self.price if self.price is not None else 0.0,
            "band_low": self.band_low,
            "band_high": self.band_high,
            "sentiment_score": self.sentiment_score,
            "rationale": self.rationale,
            "signaled_at": self.signaled_at,
        }


class SignalLogic:
    """펀더멘털 밴드 + 감성 점수 → BUY/SELL/HOLD 시그널 산출 (T-024)."""

    def __init__(
        self,
        db: Optional[DBControl] = None,
        *,
        band: Optional[FundamentalBand] = None,
        sentiment: Optional[SentimentEngine] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None
        # 하위 엔진들에 동일 db 를 공유하여 트랜잭션 자원을 절약.
        self._band = band or FundamentalBand(db=db, settings=self._settings)
        self._sentiment = sentiment or SentimentEngine(db=db, settings=self._settings)

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

    def __enter__(self) -> "SignalLogic":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ decision (T-024)
    def decide(
        self,
        *,
        stock_code: str,
        price: Optional[float],
        band: Band,
        sentiment_score: Optional[float],
        signaled_at: Optional[str] = None,
    ) -> SignalDecision:
        """순수 함수형 시그널 판별.

        - ``price/band_low/band_high/sentiment_score`` 중 하나라도 ``None`` 이면
          HOLD 로 강제 (정보 부족).
        """
        ts = signaled_at or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        if (
            price is None
            or sentiment_score is None
            or not band.is_valid
            or band.band_low is None
            or band.band_high is None
        ):
            return SignalDecision(
                stock_code=stock_code,
                signal_type="HOLD",
                price=price,
                band_low=band.band_low,
                band_high=band.band_high,
                sentiment_score=sentiment_score,
                rationale="데이터 부족(price/band/sentiment 중 누락) → HOLD",
                signaled_at=ts,
            )

        buy_th = float(self._settings.signal_sentiment_buy_threshold)
        sell_th = float(self._settings.signal_sentiment_sell_threshold)

        # PRD §F-3.2 시그널 로직.
        if price < band.band_low and sentiment_score < buy_th:
            rationale = (
                f"BUY: 현재가({price:.2f}) < 밴드 하단({band.band_low:.2f}) "
                f"& 감성({sentiment_score:.1f}) < {buy_th}"
            )
            signal_type = "BUY"
        elif price > band.band_high and sentiment_score > sell_th:
            rationale = (
                f"SELL: 현재가({price:.2f}) > 밴드 상단({band.band_high:.2f}) "
                f"& 감성({sentiment_score:.1f}) > {sell_th}"
            )
            signal_type = "SELL"
        else:
            rationale = (
                f"HOLD: 현재가={price:.2f}, 밴드=[{band.band_low:.2f},{band.band_high:.2f}], "
                f"감성={sentiment_score:.1f}"
            )
            signal_type = "HOLD"

        return SignalDecision(
            stock_code=stock_code,
            signal_type=signal_type,
            price=price,
            band_low=band.band_low,
            band_high=band.band_high,
            sentiment_score=sentiment_score,
            rationale=rationale,
            signaled_at=ts,
        )

    # ------------------------------------------------------------------ pipeline (T-025)
    def detect_and_store(self, stock_code: str) -> SignalDecision:
        """DB 에서 필요한 입력을 모아 시그널을 산출하고 ``signals`` 에 적재한다."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        db = self.db()

        latest_price_row = db.fetch_one(
            "SELECT record_date, close_price FROM financials "
            "WHERE stock_code = ? AND close_price IS NOT NULL "
            "ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        price: Optional[float] = latest_price_row["close_price"] if latest_price_row else None

        band = self._band.compute(stock_code)

        sentiment_row = self._sentiment.get_latest_score(stock_code)
        sentiment_score: Optional[float] = (
            float(sentiment_row["score"]) if sentiment_row else None
        )

        decision = self.decide(
            stock_code=stock_code,
            price=price,
            band=band,
            sentiment_score=sentiment_score,
        )

        # ensure stock exists (FK)
        db.upsert(
            "stocks",
            {"stock_code": stock_code, "name": stock_code},
            conflict_columns=["stock_code"],
            update_columns=[],  # 기존 데이터 보존
        )
        db.insert("signals", decision.to_db_row())

        _LOGGER.info(
            "시그널 적재: %s | %s | price=%s, band=[%s,%s], sentiment=%s",
            stock_code,
            decision.signal_type,
            decision.price,
            decision.band_low,
            decision.band_high,
            decision.sentiment_score,
        )
        return decision

    # ------------------------------------------------------------------ read
    def latest(self, stock_code: str) -> Optional[dict]:
        return self.db().fetch_one(
            "SELECT signal_type, price, band_low, band_high, sentiment_score, "
            "rationale, signaled_at FROM signals WHERE stock_code = ? "
            "ORDER BY signaled_at DESC LIMIT 1",
            (stock_code,),
        )
