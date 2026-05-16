"""업황 사이클 패널 (T-045, F-2.4.2).

> "중장기 투자 관점 지표를 대시보드에 표시한다."

본 모듈은 ``CycleAnalyzer.analyze_and_store`` 또는 DB 의 ``cycle_scores``
최신 row 를 받아 5단계 phase (TROUGH/EARLY/MID/LATE/PEAK) 와 점수를 시각화한다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..engine.cycle import phase_label_ko

_LOGGER = logging.getLogger(__name__)


_PHASE_COLOR = {
    "TROUGH": "#2563EB",       # 파랑 (저점)
    "EARLY_CYCLE": "#06B6D4",  # 청록 (회복)
    "MID_CYCLE": "#10B981",    # 녹색 (확장)
    "LATE_CYCLE": "#F59E0B",   # 주황 (후기)
    "PEAK": "#DC2626",         # 빨강 (정점)
}


def build_cycle_payload(cycle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """``cycle_scores`` row dict 를 표시 payload 로 변환."""
    if not cycle:
        return {
            "score": None,
            "score_pct": 50.0,
            "phase": "MID_CYCLE",
            "phase_label_ko": "데이터 없음",
            "color": "#9CA3AF",
            "score_date": "",
            "is_unknown": True,
            "metrics": {},
        }
    score = cycle.get("cycle_score")
    try:
        s = float(score) if score is not None else 0.0
    except (TypeError, ValueError):
        s = 0.0
    s = max(-100.0, min(100.0, s))
    phase = str(cycle.get("phase") or "MID_CYCLE")
    return {
        "score": score,
        "score_pct": round((s + 100.0) / 2.0, 2),
        "phase": phase,
        "phase_label_ko": phase_label_ko(phase),
        "color": _PHASE_COLOR.get(phase, "#9CA3AF"),
        "score_date": str(cycle.get("score_date") or ""),
        "is_unknown": score is None,
        "metrics": {
            "inventory_turnover": cycle.get("inventory_turnover"),
            "revenue_growth_pct": cycle.get("revenue_growth_pct"),
            "op_margin_pct": cycle.get("op_margin_pct"),
        },
    }


def render_cycle_panel(cycle: Optional[Dict[str, Any]]) -> None:
    """Streamlit 컴포넌트로 사이클 패널 렌더링."""
    try:
        import streamlit as st  # type: ignore
    except ImportError:  # pragma: no cover
        _LOGGER.error("streamlit 미설치")
        return

    payload = build_cycle_payload(cycle)
    st.markdown("#### 업황 사이클")

    if payload["is_unknown"]:
        st.info(
            "사이클 분석 결과가 아직 없습니다. "
            "관리자 화면에서 [수동 갱신] 또는 `analyze cycle` 명령을 실행하세요."
        )
        return

    cols = st.columns([3, 4])
    with cols[0]:
        st.metric(
            label="사이클 점수",
            value=f"{float(payload['score']):+.2f}",
            help="-100 (저점) ~ +100 (정점)",
        )
        st.markdown(
            f"<div style='font-size:18px; font-weight:700; color:{payload['color']};'>"
            f"{payload['phase_label_ko']}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"기준일 {payload['score_date'] or '-'}")
    with cols[1]:
        metrics = payload["metrics"] or {}
        rows = [
            {
                "지표": "재고자산 회전율",
                "값": (
                    f"{metrics['inventory_turnover']:.2f}회/연"
                    if isinstance(metrics.get("inventory_turnover"), (int, float))
                    else "N/A"
                ),
            },
            {
                "지표": "YoY 매출 성장률",
                "값": (
                    f"{metrics['revenue_growth_pct']:+.2f}%"
                    if isinstance(metrics.get("revenue_growth_pct"), (int, float))
                    else "N/A"
                ),
            },
            {
                "지표": "영업이익률",
                "값": (
                    f"{metrics['op_margin_pct']:+.2f}%"
                    if isinstance(metrics.get("op_margin_pct"), (int, float))
                    else "N/A"
                ),
            },
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
