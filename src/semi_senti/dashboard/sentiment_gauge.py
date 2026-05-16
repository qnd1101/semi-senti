"""감성 게이지 + 키워드 트렌드 컴포넌트.

Tasks 매핑
----------
- **T-033**: ``SentimentGauge`` 구현 (공포/중립/탐욕 3단계 색상 코딩)
- **T-034**: 자동 갱신 주기 (5분 interval) — ``app.py`` 에서 timer 호출
- **T-035**: 상위 기여 키워드 트렌드 리스트 표시

설계 원칙
---------
- 게이지 분류 로직은 ``data_provider.classify_sentiment`` 에 일원화.
- 본 모듈은 *순수 빌더*( ``build_gauge_payload`` )와
  *Streamlit 렌더러*( ``SentimentGauge.render`` )로 분리.
- 외부 차트 라이브러리(plotly 등) 가 없는 환경을 위해 HTML/CSS 만으로
  반원형 게이지를 직접 그린다 → 추가 의존성 0.
"""

from __future__ import annotations

import logging
from html import escape
from typing import Any, Dict, List, Optional, Sequence

from .data_provider import classify_sentiment

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Pure builders (UI 의존 X — 단위 테스트 대상)
# -----------------------------------------------------------------------------


def build_gauge_payload(sentiment: Dict[str, Any]) -> Dict[str, Any]:
    """``DataProvider.fetch_sentiment`` 결과를 게이지 렌더링 payload 로 변환.

    Returns
    -------
    dict
        ``{"score", "score_pct", "label_ko", "color", "news_count",
        "score_date", "raw_score", "is_unknown"}``
    """
    score = sentiment.get("score") if sentiment else None
    classification = sentiment.get("classification") if sentiment else None
    if not classification:
        classification = classify_sentiment(score)

    is_unknown = score is None
    # 게이지 각도 계산을 위해 -100~+100 → 0~100% 로 매핑.
    if score is None:
        score_pct = 50.0
    else:
        try:
            s = max(-100.0, min(100.0, float(score)))
        except (TypeError, ValueError):
            s = 0.0
            is_unknown = True
        score_pct = (s + 100.0) / 2.0

    return {
        "score": score,
        "score_pct": round(score_pct, 2),
        "label_ko": classification.get("label_ko", "데이터 없음"),
        "color": classification.get("color", "#9CA3AF"),
        "news_count": int(sentiment.get("news_count") or 0) if sentiment else 0,
        "score_date": str(sentiment.get("score_date") or "") if sentiment else "",
        "raw_score": sentiment.get("raw_score") if sentiment else None,
        "is_unknown": is_unknown,
    }


def build_keyword_rows(top_keywords: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """T-035: 상위 기여 키워드 표 데이터 변환.

    각 row 의 ``contribution`` 부호로 정렬된 사인 표시(▲/▼)를 함께 제공한다.
    """
    rows: List[Dict[str, Any]] = []
    for kw in top_keywords or []:
        try:
            contribution = float(kw.get("contribution") or 0.0)
        except (TypeError, ValueError):
            contribution = 0.0
        rows.append(
            {
                "word": str(kw.get("word") or "-"),
                "weight": float(kw.get("weight") or 0.0),
                "count": int(kw.get("count") or 0),
                "contribution": contribution,
                "direction": "▲" if contribution >= 0 else "▼",
                "sign_color": "#16A34A" if contribution >= 0 else "#DC2626",
            }
        )
    return rows


# -----------------------------------------------------------------------------
# Renderers (Streamlit)
# -----------------------------------------------------------------------------


_GAUGE_HTML_TEMPLATE = """
<div style="
    display: flex; flex-direction: column; align-items: center;
    padding: 12px 8px 4px 8px; font-family: 'Pretendard', sans-serif;
">
  <div style="
      position: relative; width: 220px; height: 120px; overflow: hidden;
  ">
    <div style="
        position: absolute; bottom: 0; left: 0;
        width: 220px; height: 220px;
        border-radius: 50%;
        background: conic-gradient(
            from 270deg,
            #2563EB 0deg, #2563EB 60deg,
            #6B7280 60deg, #6B7280 120deg,
            #DC2626 120deg, #DC2626 180deg,
            transparent 180deg
        );
    "></div>
    <div style="
        position: absolute; bottom: 0; left: 0;
        width: 220px; height: 220px;
        border-radius: 50%;
        background: #FFFFFF;
        transform: scale(0.78);
        transform-origin: 50% 100%;
    "></div>
    <div style="
        position: absolute; left: 110px; bottom: 0;
        width: 4px; height: 100px; background: {needle_color};
        transform-origin: 50% 100%;
        transform: rotate({needle_deg:.2f}deg);
        border-radius: 2px;
        box-shadow: 0 0 4px rgba(0,0,0,0.25);
    "></div>
    <div style="
        position: absolute; left: 102px; bottom: -8px;
        width: 16px; height: 16px; border-radius: 50%;
        background: #1F2937;
    "></div>
  </div>
  <div style="
      margin-top: 8px; font-size: 28px; font-weight: 700; color: {label_color};
  ">{score_text}</div>
  <div style="
      font-size: 14px; color: {label_color}; font-weight: 600;
      margin-top: 2px;
  ">{label_ko}</div>
  <div style="
      font-size: 11px; color: #6B7280; margin-top: 4px;
  ">{footer}</div>
</div>
"""


def _render_gauge_html(payload: Dict[str, Any]) -> str:
    """반원형 게이지를 HTML/CSS 로 렌더링한다.

    - 바늘 각도: ``-90° ~ +90°`` (점수 -100~+100 매핑)
    """
    score = payload.get("score")
    score_pct = float(payload.get("score_pct") or 50.0)
    needle_deg = (score_pct / 100.0) * 180.0 - 90.0
    if payload.get("is_unknown"):
        score_text = "N/A"
        footer = "최근 감성 점수 데이터가 없습니다."
    else:
        score_text = f"{float(score):+.1f}"
        date = escape(str(payload.get("score_date") or ""))
        news = int(payload.get("news_count") or 0)
        footer = f"기준일 {date} · 분석 뉴스 {news}건"

    return _GAUGE_HTML_TEMPLATE.format(
        needle_color=escape(str(payload.get("color") or "#1F2937")),
        needle_deg=needle_deg,
        score_text=escape(score_text),
        label_ko=escape(str(payload.get("label_ko") or "")),
        label_color=escape(str(payload.get("color") or "#1F2937")),
        footer=footer,
    )


# -----------------------------------------------------------------------------
# SentimentGauge class (T-033)
# -----------------------------------------------------------------------------


class SentimentGauge:
    """공포/중립/탐욕 게이지 + 키워드 트렌드 컴포넌트.

    Parameters
    ----------
    refresh_interval_seconds:
        게이지 자동 갱신 주기. ``app.py`` 가 본 값을 읽어 timer 를 건다 (T-034).
    """

    def __init__(self, *, refresh_interval_seconds: int = 300) -> None:
        if refresh_interval_seconds <= 0:
            raise ValueError("refresh_interval_seconds 는 1 이상이어야 합니다.")
        self._refresh_interval_seconds = int(refresh_interval_seconds)

    @property
    def refresh_interval_seconds(self) -> int:
        return self._refresh_interval_seconds

    # ------------------------------------------------------------------ pure
    @staticmethod
    def build_payload(sentiment: Dict[str, Any]) -> Dict[str, Any]:
        return build_gauge_payload(sentiment or {})

    @staticmethod
    def build_keywords(top_keywords: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return build_keyword_rows(top_keywords)

    # ------------------------------------------------------------------ render
    def render(
        self,
        sentiment: Dict[str, Any],
        *,
        title: Optional[str] = "감성 게이지",
    ) -> None:
        """Streamlit 컴포넌트로 게이지 + 키워드 표를 렌더링한다."""
        try:
            import streamlit as st  # type: ignore
        except ImportError:  # pragma: no cover
            _LOGGER.error("streamlit 미설치")
            return

        payload = self.build_payload(sentiment or {})
        keyword_rows = self.build_keywords((sentiment or {}).get("top_keywords") or [])

        if title:
            st.markdown(f"#### {title}")

        try:
            st.markdown(_render_gauge_html(payload), unsafe_allow_html=True)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("게이지 HTML 렌더링 실패: %s — 폴백", exc)
            st.metric(
                label=payload.get("label_ko", "감성"),
                value=(
                    f"{payload.get('score'):+.1f}"
                    if isinstance(payload.get("score"), (int, float))
                    else "N/A"
                ),
            )

        # T-035: 상위 키워드 트렌드 리스트
        st.markdown("##### 상위 기여 키워드")
        if not keyword_rows:
            st.caption("기여 키워드 데이터가 없습니다.")
        else:
            display_rows = [
                {
                    "방향": row["direction"],
                    "키워드": row["word"],
                    "기여도": f"{row['contribution']:+.2f}",
                    "가중치": f"{row['weight']:+.2f}",
                    "출현": row["count"],
                }
                for row in keyword_rows
            ]
            st.dataframe(display_rows, use_container_width=True, hide_index=True)
