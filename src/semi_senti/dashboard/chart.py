"""TradingView Lightweight Charts 기반 시그널 차트 컴포넌트.

Tasks 매핑
----------
- **T-028**: ``SignalChart`` 클래스 설계 + TradingView API 연동
- **T-029**: 캔들 차트 렌더링
- **T-030**: BUY(▲ 녹색) / SELL(▼ 적색) 시그널 마커
- **T-031**: 마커 호버 시 시그널 근거 팝업 (감성 점수·밴드 대비 %)
- **T-032**: 다이버전스 마커(황색 ◆ / 보라색 ◆) 오버레이

설계 원칙
---------
- 순수 *옵션 빌더*( ``build_chart_options`` )와 *Streamlit 렌더러*
  ( ``SignalChart.render`` )로 책임을 분리해 단위 테스트는 옵션 빌더만
  대상으로 한다 (UI 의존성 없는 테스트).
- ``streamlit_lightweight_charts.renderLightweightCharts`` 가 요구하는
  ``[{"chart": {...}, "series": [...]}]`` 스펙을 그대로 빌드한다.
- 라이브러리 미설치 환경에서도 import 자체는 성공하도록 lazy import.
- 마커 ``text``/``shape``/``color`` 는 PRD UI 색상 코딩 규칙(녹색/적색/황색)을 따른다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 색상 / 스타일 상수 (PRD §4.3 색상 코딩)
# -----------------------------------------------------------------------------

# T-030: 시그널 마커 색상
_BUY_COLOR = "#16A34A"   # 녹색
_SELL_COLOR = "#DC2626"  # 적색

# T-032: 다이버전스 마커 색상 (UC-04)
_DIV_BULLISH_COLOR = "#FBBF24"  # 황색 (기회)
_DIV_BEARISH_COLOR = "#8B5CF6"  # 보라색 (주의)

# F-4.3.2: 펀더멘털 밴드 라인 색상
_BAND_HIGH_COLOR = "#F87171"
_BAND_LOW_COLOR = "#60A5FA"
_BAND_MID_COLOR = "#9CA3AF"

# 캔들 색상 (한국 관행: 상승=빨강 / 하락=파랑) — PRD 기준이 별도 명시되지
# 않았으므로 ``streamlit-lightweight-charts`` 기본인 상승=녹색, 하락=빨강을
# 그대로 사용하여 BUY/SELL 마커와의 색상 충돌을 피한다.
_CANDLE_UP_COLOR = "#10B981"
_CANDLE_DOWN_COLOR = "#EF4444"


# -----------------------------------------------------------------------------
# Pure builders (UI 의존 X — 단위 테스트 대상)
# -----------------------------------------------------------------------------


def _safe_str_money(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def build_signal_markers(signals: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """T-030 / T-031: ``signals`` row 리스트를 차트 마커 dict 리스트로 변환.

    ``streamlit-lightweight-charts`` 의 ``markers`` 스펙
    (https://tradingview.github.io/lightweight-charts/) 을 따른다::

        {"time": "YYYY-MM-DD", "position": "belowBar"|"aboveBar",
         "color": "#...", "shape": "arrowUp"|"arrowDown",
         "text": "BUY", "id": "..."}

    Parameters
    ----------
    signals:
        ``DataProvider.fetch_signals`` 가 반환한 dict 의 시퀀스.

    Notes
    -----
    - HOLD 는 입력에 포함되지 않아야 하지만, 안전하게 한 번 더 필터링한다.
    - 동일 일자에 BUY/SELL 가 중복되는 경우(드물지만 가능) ``id`` 에
      정렬 인덱스를 부여하여 라이브러리가 충돌 없이 렌더링하도록 한다.
    """
    markers: List[Dict[str, Any]] = []
    for idx, sig in enumerate(signals or []):
        sig_type = str(sig.get("signal_type") or "").upper()
        if sig_type not in ("BUY", "SELL"):
            continue
        time_str = str(sig.get("time") or "")[:10]
        if not time_str:
            continue
        is_buy = sig_type == "BUY"
        markers.append(
            {
                "time": time_str,
                "position": "belowBar" if is_buy else "aboveBar",
                "color": _BUY_COLOR if is_buy else _SELL_COLOR,
                "shape": "arrowUp" if is_buy else "arrowDown",
                "text": sig_type,
                # T-031: hover 시 표기될 근거 (라이브러리에 따라 title/tooltip 으로 매핑)
                "id": f"sig-{idx}",
                "tooltip": str(sig.get("tooltip") or sig.get("rationale") or ""),
            }
        )
    return markers


def build_divergence_markers(divergences: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """T-032: 다이버전스 마커 (황색/보라색 ◆) 빌드."""
    markers: List[Dict[str, Any]] = []
    for idx, div in enumerate(divergences or []):
        time_str = str(div.get("time") or "")[:10]
        dtype = str(div.get("divergence_type") or "")
        if not time_str or dtype not in ("BULLISH_OPPORTUNITY", "BEARISH_CAUTION"):
            continue
        is_bullish = dtype == "BULLISH_OPPORTUNITY"
        markers.append(
            {
                "time": time_str,
                "position": "inBar",
                "shape": "circle",  # ◆에 가장 가까운 라이브러리 지원 모양
                "color": _DIV_BULLISH_COLOR if is_bullish else _DIV_BEARISH_COLOR,
                "text": "◆ 기회" if is_bullish else "◆ 주의",
                "id": f"div-{idx}",
                "tooltip": str(div.get("tooltip") or div.get("note") or ""),
            }
        )
    return markers


def build_band_lines(
    candles: Sequence[Dict[str, Any]],
    band: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """F-4.3.2: 차트에 오버레이할 밴드 상단/중앙/하단 수평선 데이터.

    Lightweight Charts 의 라인 시리즈는 점들을 시간 축에 그리므로,
    캔들 데이터의 첫·마지막 일자에 동일한 ``value`` 를 부여한 두 점만으로
    수평선처럼 보이게 한다.
    """
    if not candles:
        return {"high": [], "mid": [], "low": []}

    times = [str(c.get("time") or "")[:10] for c in candles if c.get("time")]
    times = [t for t in times if t]
    if not times:
        return {"high": [], "mid": [], "low": []}

    first_time, last_time = times[0], times[-1]

    def _line(value: Optional[float]) -> List[Dict[str, Any]]:
        if value is None:
            return []
        v = float(value)
        return [
            {"time": first_time, "value": v},
            {"time": last_time, "value": v},
        ]

    return {
        "high": _line(band.get("band_high")),
        "mid": _line(band.get("band_mid")),
        "low": _line(band.get("band_low")),
    }


def build_chart_options(
    candles: Sequence[Dict[str, Any]],
    signals: Sequence[Dict[str, Any]],
    divergences: Sequence[Dict[str, Any]],
    band: Dict[str, Any],
    *,
    chart_height: int = 460,
) -> List[Dict[str, Any]]:
    """``renderLightweightCharts`` 가 요구하는 ``charts`` 인자 빌드.

    Returns
    -------
    list of dict
        길이 1 리스트(차트 1개). ``[{"chart": {...}, "series": [...]}]``
    """
    markers = build_signal_markers(signals) + build_divergence_markers(divergences)
    band_lines = build_band_lines(candles, band)

    chart_config: Dict[str, Any] = {
        "height": int(chart_height),
        "layout": {
            "background": {"type": "solid", "color": "#FFFFFF"},
            "textColor": "#1F2937",
        },
        "grid": {
            "vertLines": {"color": "#E5E7EB"},
            "horzLines": {"color": "#E5E7EB"},
        },
        "rightPriceScale": {"borderColor": "#D1D5DB"},
        "timeScale": {
            "borderColor": "#D1D5DB",
            "timeVisible": False,
            "secondsVisible": False,
        },
        "crosshair": {"mode": 1},
        "watermark": {
            "visible": True,
            "fontSize": 14,
            "color": "rgba(0, 0, 0, 0.05)",
            "text": "Semi Senti",
        },
    }

    series: List[Dict[str, Any]] = []

    # 1) 캔들 시리즈 (T-029)
    series.append(
        {
            "type": "Candlestick",
            "data": list(candles),
            "options": {
                "upColor": _CANDLE_UP_COLOR,
                "downColor": _CANDLE_DOWN_COLOR,
                "borderUpColor": _CANDLE_UP_COLOR,
                "borderDownColor": _CANDLE_DOWN_COLOR,
                "wickUpColor": _CANDLE_UP_COLOR,
                "wickDownColor": _CANDLE_DOWN_COLOR,
            },
            "markers": markers,
        }
    )

    # 2) 펀더멘털 밴드 라인 (F-4.3.2) — 데이터가 있을 때만 추가
    if band_lines["high"]:
        series.append(
            {
                "type": "Line",
                "data": band_lines["high"],
                "options": {
                    "color": _BAND_HIGH_COLOR,
                    "lineWidth": 1,
                    "lineStyle": 2,  # dashed
                    "title": "밴드 상단",
                    "priceLineVisible": False,
                },
            }
        )
    if band_lines["mid"]:
        series.append(
            {
                "type": "Line",
                "data": band_lines["mid"],
                "options": {
                    "color": _BAND_MID_COLOR,
                    "lineWidth": 1,
                    "lineStyle": 3,  # dotted
                    "title": "밴드 중앙",
                    "priceLineVisible": False,
                },
            }
        )
    if band_lines["low"]:
        series.append(
            {
                "type": "Line",
                "data": band_lines["low"],
                "options": {
                    "color": _BAND_LOW_COLOR,
                    "lineWidth": 1,
                    "lineStyle": 2,
                    "title": "밴드 하단",
                    "priceLineVisible": False,
                },
            }
        )

    return [{"chart": chart_config, "series": series}]


# -----------------------------------------------------------------------------
# SignalChart class (T-028)
# -----------------------------------------------------------------------------


class SignalChart:
    """반도체 종목 캔들 차트 + 시그널/다이버전스 마커 컴포넌트.

    Parameters
    ----------
    height:
        차트 픽셀 높이. PRD §4.3 1화면 집중 원칙을 위해 460px 기본값.
    """

    def __init__(self, *, height: int = 460) -> None:
        self._height = int(height)

    # ------------------------------------------------------------------ pure
    def build(
        self,
        *,
        candles: Sequence[Dict[str, Any]],
        signals: Sequence[Dict[str, Any]],
        divergences: Sequence[Dict[str, Any]],
        band: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """차트 옵션 dict 만 반환 (UI 비의존). 단위 테스트의 진입점."""
        return build_chart_options(
            candles=candles,
            signals=signals,
            divergences=divergences,
            band=band,
            chart_height=self._height,
        )

    # ------------------------------------------------------------------ render
    def render(
        self,
        *,
        candles: Sequence[Dict[str, Any]],
        signals: Sequence[Dict[str, Any]],
        divergences: Sequence[Dict[str, Any]],
        band: Dict[str, Any],
        key: str = "semi-senti-chart",
    ) -> None:
        """Streamlit 화면에 차트를 그린다. 라이브러리 미설치 시 폴백."""
        try:
            import streamlit as st  # type: ignore
        except ImportError:  # pragma: no cover - 런타임 의존성 부재
            _LOGGER.error("streamlit 이 설치되어 있지 않습니다.")
            return

        if not candles:
            # UC-02 §E1 텍스트 폴백 — 데이터 없음 시 빈 차트 대신 안내 문구.
            st.info("표시할 가격 데이터가 없습니다. 종목을 갱신해 주세요.")
            self._render_signal_table(signals)
            return

        try:
            from streamlit_lightweight_charts import renderLightweightCharts  # type: ignore
        except ImportError:
            # 라이브러리 부재 시 텍스트 기반 시그널 요약 + Streamlit 기본 차트 폴백.
            _LOGGER.warning("streamlit-lightweight-charts 미설치 — 텍스트 폴백 사용")
            st.warning(
                "차트 라이브러리가 설치되지 않아 단순 가격 라인을 표시합니다. "
                "(`pip install streamlit-lightweight-charts`)"
            )
            try:
                # pandas/streamlit 가 있다면 line_chart 로 폴백.
                import pandas as pd  # type: ignore

                df = pd.DataFrame(candles)
                if not df.empty and "close" in df.columns:
                    df = df.set_index("time")
                    st.line_chart(df["close"])
            except Exception:  # pylint: disable=broad-except
                pass
            self._render_signal_table(signals)
            return

        options = self.build(
            candles=candles,
            signals=signals,
            divergences=divergences,
            band=band,
        )
        try:
            # 위치 인자로 호출 (라이브러리 시그니처: renderLightweightCharts(charts, key))
            renderLightweightCharts(options, key)
        except Exception as exc:  # pylint: disable=broad-except
            # UC-02 §E1 — TradingView 렌더링 실패 시 텍스트 시그널 표.
            _LOGGER.error("차트 렌더링 실패: %s", exc)
            st.error("차트를 불러올 수 없습니다. 텍스트 기반 시그널 요약으로 대체합니다.")
            self._render_signal_table(signals)
            return

        # T-031: 호버 팝업이 라이브러리에서 노출되지 않을 수 있어,
        # 마커 위치별 근거 표를 Expander 로 함께 제공하여 접근성을 보강한다.
        if signals or divergences:
            with st.expander("마커 근거 자세히 보기", expanded=False):
                self._render_signal_table(signals)
                self._render_divergence_table(divergences)

    # ------------------------------------------------------------------ fallback tables
    @staticmethod
    def _render_signal_table(signals: Sequence[Dict[str, Any]]) -> None:
        try:
            import streamlit as st  # type: ignore
        except ImportError:  # pragma: no cover
            return
        if not signals:
            st.caption("최근 BUY/SELL 시그널이 없습니다. (현재 구간: HOLD)")
            return
        rows = []
        for sig in signals:
            rows.append(
                {
                    "일자": str(sig.get("time") or "")[:10],
                    "시그널": sig.get("signal_type"),
                    "현재가": _safe_str_money(sig.get("price")),
                    "감성": (
                        f"{sig.get('sentiment_score'):+.1f}"
                        if isinstance(sig.get("sentiment_score"), (int, float))
                        else "-"
                    ),
                    "근거": sig.get("tooltip") or sig.get("rationale") or "",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    @staticmethod
    def _render_divergence_table(divergences: Sequence[Dict[str, Any]]) -> None:
        try:
            import streamlit as st  # type: ignore
        except ImportError:  # pragma: no cover
            return
        if not divergences:
            return
        rows = []
        for div in divergences:
            rows.append(
                {
                    "일자": str(div.get("time") or "")[:10],
                    "유형": div.get("label"),
                    "주가 변화": (
                        f"{div.get('price_change_pct'):+.2f}%"
                        if isinstance(div.get("price_change_pct"), (int, float))
                        else "-"
                    ),
                    "감성 변화": (
                        f"{div.get('sentiment_change_pt'):+.2f}pt"
                        if isinstance(div.get("sentiment_change_pt"), (int, float))
                        else "-"
                    ),
                    "근거": div.get("tooltip") or div.get("note") or "",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
