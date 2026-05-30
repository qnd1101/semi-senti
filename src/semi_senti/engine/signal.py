"""다중 관점 매매 시그널 산출 및 적재 (F-3.2, PRD v1.2).

PRD §F-3.2 의사코드 기반 Short/Mid/Long 독립 시그널 산출.

관점별 가중치 모델:
    단기 (SHORT, 1일~2주):
        score = 0.45 * S_news + 0.35 * Price_D + 0.20 * (-Valuation_pos * 100)

    중기 (MID, 2주~3개월):
        score = 0.25 * S_news + 0.30 * Price_W + 0.35 * (-Valuation_pos * 100) + 0.10 * K_trend

    장기 (LONG, 3개월~12개월+):
        score = 0.10 * S_news + 0.20 * Price_M + 0.35 * (-Valuation_pos * 100)
                + 0.20 * Cycle_score + 0.15 * Inventory_z

판정 규칙 (관점별 독립):
    score >= +25  → BUY
    score <= -25  → SELL
    else          → HOLD
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl
from .band import Band, FundamentalBand
from .sentiment import SentimentEngine

_LOGGER = logging.getLogger(__name__)

Perspective = str  # 'SHORT' | 'MID' | 'LONG'
SignalType = str   # 'BUY' | 'SELL' | 'HOLD'

PERSPECTIVES: List[Perspective] = ["SHORT", "MID", "LONG"]


@dataclass
class PerspectiveScore:
    """관점 하나의 입력 점수 집합."""

    perspective: Perspective
    s_news: float = 0.0       # 뉴스 감성 점수 (-100 ~ +100)
    price_d: float = 0.0      # 일봉 추세 점수 (-100 ~ +100)
    price_w: float = 0.0      # 주봉 추세 점수 (-100 ~ +100)
    price_m: float = 0.0      # 월봉 추세 점수 (-100 ~ +100)
    valuation_pos: float = 0.0  # 밴드 내 위치 (-1 ~ +1)
    k_trend: float = 0.0      # 키워드 모멘텀 점수 (-100 ~ +100)
    cycle_score: float = 0.0  # 업황 사이클 점수 (-100 ~ +100)
    inventory_z: float = 0.0  # 재고자산 회전율 표준화


@dataclass
class SignalDecision:
    """단일 관점의 시그널 산출 결과."""

    stock_code: str
    perspective: Perspective
    signal_type: SignalType
    score: float
    price: Optional[float]
    band_low: Optional[float]
    band_high: Optional[float]
    sentiment_score: Optional[float]
    rationale: str
    signaled_at: str

    def to_db_row(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "perspective": self.perspective,
            "signal_type": self.signal_type,
            "score": round(self.score, 4),
            "price": self.price if self.price is not None else 0.0,
            "band_low": self.band_low,
            "band_high": self.band_high,
            "sentiment_score": self.sentiment_score,
            "rationale": self.rationale,
            "signaled_at": self.signaled_at,
        }


@dataclass
class MultiPerspectiveResult:
    """3개 관점 통합 결과."""

    stock_code: str
    short: Optional[SignalDecision] = None
    mid: Optional[SignalDecision] = None
    long: Optional[SignalDecision] = None

    @property
    def decisions(self) -> List[SignalDecision]:
        return [d for d in [self.short, self.mid, self.long] if d is not None]

    def as_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "short": _decision_to_dict(self.short),
            "mid": _decision_to_dict(self.mid),
            "long": _decision_to_dict(self.long),
        }


def _decision_to_dict(d: Optional[SignalDecision]) -> Optional[dict]:
    if d is None:
        return None
    return {
        "perspective": d.perspective,
        "signal_type": d.signal_type,
        "score": d.score,
        "price": d.price,
        "band_low": d.band_low,
        "band_high": d.band_high,
        "sentiment_score": d.sentiment_score,
        "rationale": d.rationale,
        "signaled_at": d.signaled_at,
    }


def _price_trend(prices: List[float], window: int) -> float:
    """최근 `window` 거래일의 가격 추세 점수 (-100 ~ +100).

    단순 선형 회귀 기울기를 최초 가격으로 정규화.
    """
    if len(prices) < 2:
        return 0.0
    p = prices[-min(window, len(prices)):]
    if len(p) < 2:
        return 0.0
    n = len(p)
    xs = list(range(n))
    mean_x = (n - 1) / 2
    mean_y = sum(p) / n
    num = sum((xs[i] - mean_x) * (p[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    slope = num / den
    base = p[0] if p[0] != 0 else 1.0
    # 일 단위 기울기 → 퍼센트 정규화 → tanh 스케일 (-100~+100)
    rel_slope = slope / base * 100
    return max(-100.0, min(100.0, math.tanh(rel_slope / 10) * 100))


class SignalLogic:
    """PRD §F-3.2 가중치 모델 기반 Short/Mid/Long 독립 시그널 산출."""

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
        self._band = band or FundamentalBand(db=db, settings=self._settings)
        self._sentiment = sentiment or SentimentEngine(db=db, settings=self._settings)

    # ------------------------------------------------------------------ life
    def db(self) -> DBControl:
        if self._db is None:
            self._db = DBControl()
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

    # ------------------------------------------------------------------ core
    def _compute_short(self, ps: PerspectiveScore) -> float:
        """단기 관점 점수 산출."""
        return (
            0.45 * ps.s_news
            + 0.35 * ps.price_d
            + 0.20 * (-ps.valuation_pos * 100)
        )

    def _compute_mid(self, ps: PerspectiveScore) -> float:
        """중기 관점 점수 산출."""
        return (
            0.25 * ps.s_news
            + 0.30 * ps.price_w
            + 0.35 * (-ps.valuation_pos * 100)
            + 0.10 * ps.k_trend
        )

    def _compute_long(self, ps: PerspectiveScore) -> float:
        """장기 관점 점수 산출."""
        return (
            0.10 * ps.s_news
            + 0.20 * ps.price_m
            + 0.35 * (-ps.valuation_pos * 100)
            + 0.20 * ps.cycle_score
            + 0.15 * ps.inventory_z
        )

    def _classify(self, score: float, perspective: Perspective) -> SignalType:
        buy_th = float(getattr(self._settings, f"signal_{perspective.lower()}_buy_threshold", 25))
        sell_th = float(getattr(self._settings, f"signal_{perspective.lower()}_sell_threshold", -25))
        if score >= buy_th:
            return "BUY"
        if score <= sell_th:
            return "SELL"
        return "HOLD"

    def decide_perspective(
        self,
        *,
        stock_code: str,
        perspective: Perspective,
        ps: PerspectiveScore,
        price: Optional[float],
        band: Band,
        ts: str,
    ) -> SignalDecision:
        """단일 관점 시그널 판별."""
        if perspective == "SHORT":
            score = self._compute_short(ps)
        elif perspective == "MID":
            score = self._compute_mid(ps)
        else:
            score = self._compute_long(ps)

        signal_type = self._classify(score, perspective)

        rationale = (
            f"{perspective}/{signal_type}: score={score:.2f}, "
            f"s_news={ps.s_news:.1f}, "
            f"price_d={ps.price_d:.1f}, price_w={ps.price_w:.1f}, "
            f"valuation_pos={ps.valuation_pos:.3f}, "
            f"band=[{band.band_low},{band.band_high}], price={price}"
        )
        return SignalDecision(
            stock_code=stock_code,
            perspective=perspective,
            signal_type=signal_type,
            score=round(score, 4),
            price=price,
            band_low=band.band_low,
            band_high=band.band_high,
            sentiment_score=ps.s_news,
            rationale=rationale,
            signaled_at=ts,
        )

    # ------------------------------------------------------------------ pipeline
    def detect_and_store(self, stock_code: str) -> MultiPerspectiveResult:
        """DB 에서 입력 데이터를 수집해 3관점 시그널을 산출하고 ``signals`` 에 적재한다."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        db = self.db()
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

        # --- 최신 종가
        price_rows = db.fetch_all(
            "SELECT close_price FROM financials "
            "WHERE stock_code = %s AND close_price IS NOT NULL "
            "ORDER BY record_date DESC LIMIT 30",
            (stock_code,),
        )
        prices = [float(r["close_price"]) for r in price_rows if r.get("close_price")]
        current_price: Optional[float] = prices[0] if prices else None

        # --- 펀더멘털 밴드
        band = self._band.compute(stock_code)

        # --- 밴드 내 위치 (-1 ~ +1)
        valuation_pos = 0.0
        if band.is_valid and band.band_low and band.band_high and current_price is not None:
            mid = (band.band_low + band.band_high) / 2
            span = band.band_high - band.band_low
            if span > 0:
                valuation_pos = max(-1.0, min(1.0, (current_price - mid) / span))

        # --- 감성 점수
        sentiment_row = self._sentiment.get_latest_score(stock_code)
        s_news = float(sentiment_row["score"]) if sentiment_row else 0.0

        # --- 키워드 트렌드 점수 (최근 감성 점수 N일 기울기)
        sent_rows = db.fetch_all(
            "SELECT score FROM sentiment_scores "
            "WHERE stock_code = %s ORDER BY score_date DESC LIMIT 10",
            (stock_code,),
        )
        sent_scores = [float(r["score"]) for r in sent_rows if r.get("score") is not None]
        k_trend = _price_trend(list(reversed(sent_scores)), 10)

        # --- 가격 추세 점수 (일/주/월)
        price_d = _price_trend(list(reversed(prices)), 5)   # 최근 5거래일
        price_w = _price_trend(list(reversed(prices)), 15)  # 최근 15거래일(~3주)
        price_m = _price_trend(list(reversed(prices)), 30)  # 최근 30거래일(~1개월)

        # --- 업황 사이클 점수
        cycle_row = db.fetch_one(
            "SELECT cycle_score, inventory_turnover FROM cycle_scores "
            "WHERE stock_code = %s ORDER BY score_date DESC LIMIT 1",
            (stock_code,),
        )
        cycle_score = float(cycle_row["cycle_score"]) if cycle_row else 0.0
        inv_turnover = float(cycle_row["inventory_turnover"] or 0) if cycle_row else 0.0
        # 재고 회전율 표준화 (설정 기준점 대비)
        inv_target = float(self._settings.cycle_inventory_target)
        inv_span = float(self._settings.cycle_inventory_span)
        inventory_z = max(-100.0, min(100.0, (inv_turnover - inv_target) / inv_span * 50)) if inv_span else 0.0

        # --- stocks FK 보장
        db.upsert(
            "stocks",
            {"stock_code": stock_code, "name": stock_code},
            conflict_columns=["stock_code"],
            update_columns=[],
        )

        ps = PerspectiveScore(
            perspective="SHORT",
            s_news=s_news,
            price_d=price_d,
            price_w=price_w,
            price_m=price_m,
            valuation_pos=valuation_pos,
            k_trend=k_trend,
            cycle_score=cycle_score,
            inventory_z=inventory_z,
        )

        result = MultiPerspectiveResult(stock_code=stock_code)
        for persp in PERSPECTIVES:
            ps.perspective = persp
            decision = self.decide_perspective(
                stock_code=stock_code,
                perspective=persp,
                ps=ps,
                price=current_price,
                band=band,
                ts=ts,
            )
            db.insert("signals", decision.to_db_row())
            if persp == "SHORT":
                result.short = decision
            elif persp == "MID":
                result.mid = decision
            else:
                result.long = decision

            _LOGGER.info(
                "시그널 적재: %s | %s | %s | score=%.2f",
                stock_code,
                persp,
                decision.signal_type,
                decision.score,
            )

        return result

    # ------------------------------------------------------------------ read
    def latest(self, stock_code: str, perspective: Optional[str] = None) -> Optional[dict]:
        """가장 최근 시그널 1건. perspective 미지정 시 SHORT."""
        p = (perspective or "SHORT").upper()
        return self.db().fetch_one(
            "SELECT perspective, signal_type, score, price, band_low, band_high, "
            "sentiment_score, rationale, signaled_at FROM signals "
            "WHERE stock_code = %s AND perspective = %s "
            "ORDER BY signaled_at DESC LIMIT 1",
            (stock_code, p),
        )

    def latest_all(self, stock_code: str) -> Dict[str, Optional[dict]]:
        """SHORT/MID/LONG 각 관점 최신 시그널."""
        result: Dict[str, Optional[dict]] = {}
        for persp in PERSPECTIVES:
            result[persp.lower()] = self.latest(stock_code, perspective=persp)
        return result
