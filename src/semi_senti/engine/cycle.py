"""반도체 업황 사이클 분석 (T-044, T-045, F-2.4).

> "F-2.4.1 재고자산 회전율과 분기별 재무 지표를 분석하여 현재 업황의
>  사이클 위치를 수치화한다."
> "F-2.4.2 중장기 투자 관점 지표를 대시보드에 표시한다."

수치화 모델 (Phase 4 초안)
-------------------------
사이클 점수(``cycle_score``)는 -100 ~ +100 범위로 정규화된 단일 스코어이며,
다음 세 입력의 가중 합으로 산출한다.

1. **재고자산 회전율(Inventory Turnover)**
   - DART 의 ``재고자산`` 과 ``매출액`` 으로 계산: ``revenue / inventory``.
   - 회전율이 *높을수록* 호황(공급 부족 → 빠른 소화) → +방향.
2. **YoY 매출 성장률(%)**
   - 동기 대비 매출 성장률. +성장은 사이클 상승국면.
3. **영업이익률(%)**
   - 마진 확대는 사이클 후기·정점 신호로 간주.

각 신호를 ``-1~+1`` 로 정규화한 뒤 가중 평균하여 100 을 곱한다.

사이클 phase 분류
-----------------
- ``cycle_score >=  60``: PEAK (고점)
- ``cycle_score >=  20``: LATE_CYCLE
- ``cycle_score >  -20``: MID_CYCLE
- ``cycle_score >  -60``: EARLY_CYCLE
- ``cycle_score <= -60``: TROUGH (저점)

본 모델은 *해석 가능성* 을 우선하는 단순 가중합이며, 정밀 모델링은 별도
실험 노트북에서 다룬다 (해석 단순화 = 1인 개발자 운영 원칙).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)


CyclePhase = str  # 'TROUGH' | 'EARLY_CYCLE' | 'MID_CYCLE' | 'LATE_CYCLE' | 'PEAK'

# Phase 분류 임계값 (cycle_score 기준)
_PHASE_THRESHOLDS = (
    (-60.0, "TROUGH"),
    (-20.0, "EARLY_CYCLE"),
    (20.0, "MID_CYCLE"),
    (60.0, "LATE_CYCLE"),
    (100.0, "PEAK"),
)

_PHASE_LABEL_KO = {
    "TROUGH": "저점 (회복 임박)",
    "EARLY_CYCLE": "회복 초입",
    "MID_CYCLE": "확장 국면",
    "LATE_CYCLE": "후기 호황",
    "PEAK": "정점 (조정 임박)",
}


@dataclass
class CycleResult:
    """사이클 분석 결과."""

    stock_code: str
    score_date: str                 # 'YYYY-MM-DD'
    cycle_score: float              # -100 ~ +100
    phase: CyclePhase
    inventory_turnover: Optional[float]
    revenue_growth_pct: Optional[float]
    op_margin_pct: Optional[float]
    note: str
    sample_size: int = 0

    @property
    def phase_label_ko(self) -> str:
        return _PHASE_LABEL_KO.get(self.phase, self.phase)

    def to_db_row(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "score_date": self.score_date,
            "cycle_score": float(self.cycle_score),
            "phase": self.phase,
            "inventory_turnover": self.inventory_turnover,
            "revenue_growth_pct": self.revenue_growth_pct,
            "op_margin_pct": self.op_margin_pct,
            "note": self.note,
        }


# -----------------------------------------------------------------------------
# Pure functions (단위 테스트 대상)
# -----------------------------------------------------------------------------


def classify_phase(cycle_score: Optional[float]) -> CyclePhase:
    """``cycle_score`` 를 5단계 phase 로 분류."""
    if cycle_score is None:
        return "MID_CYCLE"
    try:
        s = float(cycle_score)
    except (TypeError, ValueError):
        return "MID_CYCLE"
    s = max(-100.0, min(100.0, s))
    for upper, phase in _PHASE_THRESHOLDS:
        if s <= upper:
            return phase
    return "PEAK"


def _clamp01(value: float, *, target: float, span: float) -> float:
    """``value`` 를 ``target ± span`` 기준으로 -1~+1 로 매핑."""
    if span <= 0:
        return 0.0
    diff = (value - target) / span
    return max(-1.0, min(1.0, diff))


def compute_cycle_score(
    *,
    inventory_turnover: Optional[float],
    revenue_growth_pct: Optional[float],
    op_margin_pct: Optional[float],
    weights: Optional[Dict[str, float]] = None,
    targets: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[float]:
    """세 가지 입력을 가중 평균 → -100~+100 사이클 점수.

    Parameters
    ----------
    inventory_turnover:
        매출 / 재고자산. 반도체 업종 평균을 4 회/연 가정.
    revenue_growth_pct:
        YoY 매출 성장률. ``+10%`` 면 강한 상승.
    op_margin_pct:
        영업이익률. ``+15%`` 면 마진 확대 단계.
    weights:
        각 신호의 가중치. 기본 (0.4, 0.4, 0.2).
    targets:
        각 신호의 (target, span). 기본은 반도체 업종 일반치.

    Returns
    -------
    float | None
        모든 입력이 ``None`` 이면 ``None``.
    """
    weights = weights or {"inventory": 0.4, "revenue": 0.4, "margin": 0.2}
    targets = targets or {
        "inventory": {"target": 4.0, "span": 2.0},
        "revenue": {"target": 0.0, "span": 20.0},
        "margin": {"target": 10.0, "span": 15.0},
    }

    pieces: List[float] = []
    used_weights: List[float] = []

    if inventory_turnover is not None:
        pieces.append(
            _clamp01(
                float(inventory_turnover),
                target=targets["inventory"]["target"],
                span=targets["inventory"]["span"],
            )
        )
        used_weights.append(weights["inventory"])
    if revenue_growth_pct is not None:
        pieces.append(
            _clamp01(
                float(revenue_growth_pct),
                target=targets["revenue"]["target"],
                span=targets["revenue"]["span"],
            )
        )
        used_weights.append(weights["revenue"])
    if op_margin_pct is not None:
        pieces.append(
            _clamp01(
                float(op_margin_pct),
                target=targets["margin"]["target"],
                span=targets["margin"]["span"],
            )
        )
        used_weights.append(weights["margin"])

    if not pieces:
        return None
    total_weight = sum(used_weights)
    if total_weight <= 0:
        return None
    weighted = sum(p * w for p, w in zip(pieces, used_weights)) / total_weight
    return round(max(-100.0, min(100.0, weighted * 100.0)), 2)


def phase_label_ko(phase: CyclePhase) -> str:
    return _PHASE_LABEL_KO.get(phase, phase)


# -----------------------------------------------------------------------------
# CycleAnalyzer
# -----------------------------------------------------------------------------


class CycleAnalyzer:
    """``financials`` 테이블에서 사이클 점수를 산출하고 ``cycle_scores`` 에 적재.

    Notes
    -----
    - 본 클래스는 분기 재무 데이터를 지난 4분기까지 모아 ``revenue / inventory``
      등을 계산한다. 현재 ``financials`` 테이블에는 재고자산 컬럼이 없으므로,
      입력으로 직접 지정하거나(``compute_with_inputs``) revenue·op_profit 만으로
      축약 산출하는 폴백 경로(``compute_from_db``)를 함께 제공한다.
    """

    INVENTORY_KEY = "inventory"  # collector 에서 별도 컬럼으로 적재 시 활용 (Phase 4+)

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

    def __enter__(self) -> "CycleAnalyzer":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ pure-input pipeline (T-044)
    def compute_with_inputs(
        self,
        *,
        stock_code: str,
        score_date: Optional[str] = None,
        inventory_turnover: Optional[float] = None,
        revenue_growth_pct: Optional[float] = None,
        op_margin_pct: Optional[float] = None,
    ) -> CycleResult:
        """입력값이 명시적으로 주어진 경우의 산출 (테스트/외부 데이터 연동 용도)."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")
        targets = {
            "inventory": {
                "target": float(self._settings.cycle_inventory_target),
                "span": float(self._settings.cycle_inventory_span),
            },
            "revenue": {
                "target": float(self._settings.cycle_revenue_target),
                "span": float(self._settings.cycle_revenue_span),
            },
            "margin": {
                "target": float(self._settings.cycle_margin_target),
                "span": float(self._settings.cycle_margin_span),
            },
        }
        score = compute_cycle_score(
            inventory_turnover=inventory_turnover,
            revenue_growth_pct=revenue_growth_pct,
            op_margin_pct=op_margin_pct,
            targets=targets,
        )
        phase = classify_phase(score)
        date = score_date or datetime.utcnow().strftime("%Y-%m-%d")
        note_parts = [
            f"phase={phase}",
            f"inv_turnover={inventory_turnover}",
            f"rev_yoy={revenue_growth_pct}",
            f"op_margin={op_margin_pct}",
        ]
        return CycleResult(
            stock_code=stock_code,
            score_date=date,
            cycle_score=float(score) if score is not None else 0.0,
            phase=phase,
            inventory_turnover=inventory_turnover,
            revenue_growth_pct=revenue_growth_pct,
            op_margin_pct=op_margin_pct,
            note=" | ".join(note_parts),
            sample_size=int(
                bool(inventory_turnover is not None)
                + bool(revenue_growth_pct is not None)
                + bool(op_margin_pct is not None)
            ),
        )

    # ------------------------------------------------------------------ DB-driven pipeline (T-044, T-045)
    def compute_from_db(
        self,
        stock_code: str,
        *,
        score_date: Optional[str] = None,
    ) -> CycleResult:
        """``financials`` 테이블에서 가용한 분기 지표를 모아 사이클 점수를 산출.

        - 현재 스키마에 재고자산 컬럼이 없으므로 inventory_turnover 는 ``None``.
        - YoY 매출 성장률은 가장 최근 비-NULL revenue 와 약 1년 전(±60일) 비-NULL
          revenue 를 비교해 계산한다.
        - 영업이익률은 revenue 가 0보다 클 때만 산출한다.
        """
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        rows = self.db().fetch_all(
            "SELECT record_date, revenue, operating_profit "
            "FROM financials WHERE stock_code = ? "
            "AND (revenue IS NOT NULL OR operating_profit IS NOT NULL) "
            "ORDER BY record_date DESC",
            (stock_code,),
        )
        latest = next(
            (r for r in rows if r.get("revenue") is not None), None
        )
        revenue_growth_pct = self._compute_revenue_growth(rows)
        op_margin_pct = self._compute_op_margin(latest)

        date = score_date or (
            (latest or {}).get("record_date")
            or datetime.utcnow().strftime("%Y-%m-%d")
        )
        date = str(date)[:10]

        return self.compute_with_inputs(
            stock_code=stock_code,
            score_date=date,
            inventory_turnover=None,
            revenue_growth_pct=revenue_growth_pct,
            op_margin_pct=op_margin_pct,
        )

    def analyze_and_store(
        self,
        stock_code: str,
        *,
        score_date: Optional[str] = None,
    ) -> CycleResult:
        """``compute_from_db`` + ``cycle_scores`` UPSERT (T-045)."""
        result = self.compute_from_db(stock_code, score_date=score_date)
        self.db().upsert(
            "cycle_scores",
            result.to_db_row(),
            conflict_columns=["stock_code", "score_date"],
            update_columns=[
                "cycle_score",
                "phase",
                "inventory_turnover",
                "revenue_growth_pct",
                "op_margin_pct",
                "note",
            ],
        )
        _LOGGER.info(
            "cycle 적재: stock=%s date=%s score=%.2f phase=%s",
            stock_code, result.score_date, result.cycle_score, result.phase,
        )
        return result

    # ------------------------------------------------------------------ read
    def latest(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """대시보드에서 사용할 최신 사이클 결과 1건."""
        return self.db().fetch_one(
            "SELECT score_date, cycle_score, phase, inventory_turnover, "
            "revenue_growth_pct, op_margin_pct, note, created_at "
            "FROM cycle_scores WHERE stock_code = ? "
            "ORDER BY score_date DESC LIMIT 1",
            (stock_code,),
        )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _compute_revenue_growth(rows: List[Dict[str, Any]]) -> Optional[float]:
        """가장 최근 revenue 와 약 1년 전(>=300일 차이) 비-NULL revenue 비교."""
        revenues = [
            (str(r.get("record_date") or "")[:10], r.get("revenue"))
            for r in rows
            if r.get("revenue") is not None and r.get("record_date")
        ]
        if len(revenues) < 2:
            return None
        latest_date, latest_value = revenues[0]
        try:
            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
        except ValueError:
            return None

        for date_str, value in revenues[1:]:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            delta_days = abs((latest_dt - dt).days)
            if delta_days >= 300 and float(value) != 0:
                growth = (float(latest_value) - float(value)) / float(value) * 100.0
                return round(growth, 2)
        return None

    @staticmethod
    def _compute_op_margin(latest_row: Optional[Dict[str, Any]]) -> Optional[float]:
        if not latest_row:
            return None
        revenue = latest_row.get("revenue")
        op = latest_row.get("operating_profit")
        if revenue in (None, 0) or op is None:
            return None
        try:
            return round(float(op) / float(revenue) * 100.0, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
