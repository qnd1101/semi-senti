"""재무 요약 패널 (T-036, F-4.3).

> "F-4.3.1 종목 선택 시 매출액·영업이익·PER·PBR·EPS 등 핵심 재무 지표를
>  요약하여 한 화면에 표시한다."

설계 원칙
---------
- 본 모듈도 *순수 포맷터*( ``format_metric_rows`` )와 *Streamlit 렌더러*
  ( ``FinancialSummary.render`` )로 분리.
- 큰 금액(매출액·영업이익)은 자동으로 억/조 단위로 축약하여 가독성을 높인다.
- 결측 지표는 'N/A' 로 표시하되, 패널 자체는 항상 노출하여 1화면 집중 원칙
  (PRD §4.3) 을 만족한다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 표기 단위 변환 유틸 (KRW 기준)
# -----------------------------------------------------------------------------


def _format_currency(value: Optional[float], currency: str = "KRW") -> str:
    """금액을 한국어 친화 단위(조/억/만)로 축약."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"

    sign = "-" if v < 0 else ""
    abs_v = abs(v)
    if currency.upper() == "KRW":
        if abs_v >= 1_000_000_000_000:
            return f"{sign}{abs_v / 1_000_000_000_000:,.2f}조 원"
        if abs_v >= 100_000_000:
            return f"{sign}{abs_v / 100_000_000:,.2f}억 원"
        if abs_v >= 10_000:
            return f"{sign}{abs_v / 10_000:,.2f}만 원"
        return f"{sign}{abs_v:,.0f}원"
    return f"{sign}{abs_v:,.2f} {currency}"


def _format_price(value: Optional[float], currency: str = "KRW") -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if currency.upper() == "KRW":
        return f"{v:,.0f}원"
    return f"{v:,.2f} {currency}"


def _format_ratio(value: Optional[float], suffix: str = "") -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{v:,.2f}{suffix}"


# -----------------------------------------------------------------------------
# Pure builders
# -----------------------------------------------------------------------------


def format_metric_rows(
    financial: Dict[str, Any],
    band: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str, str]]:
    """metric 표시용 (라벨, 값, 부가설명) 튜플 리스트 반환.

    Streamlit 의 ``st.metric`` 가 요구하는 형식에 맞춘다.
    """
    if financial is None:
        financial = {}
    if band is None:
        band = {}
    currency = str(financial.get("currency") or "KRW")

    current_price = financial.get("current_price")
    record_date = financial.get("record_date") or "-"

    rows: List[Tuple[str, str, str]] = [
        (
            "현재가",
            _format_price(current_price, currency),
            f"기준일 {record_date}",
        ),
        (
            "매출액",
            _format_currency(financial.get("revenue"), currency),
            "최근 보고 기준",
        ),
        (
            "영업이익",
            _format_currency(financial.get("operating_profit"), currency),
            "최근 보고 기준",
        ),
        (
            "PER",
            _format_ratio(financial.get("per"), "배"),
            "주가수익비율",
        ),
        (
            "PBR",
            _format_ratio(financial.get("pbr"), "배"),
            "주가순자산비율",
        ),
        (
            "EPS",
            _format_price(financial.get("eps"), currency),
            "주당순이익",
        ),
    ]
    return rows


def build_band_summary(
    financial: Dict[str, Any],
    band: Dict[str, Any],
) -> Dict[str, Any]:
    """현재가 ↔ 펀더멘털 밴드(상단/하단) 비교 요약.

    UC-02 §시그널 산출 로직의 입력값을 한 줄로 보여주는 데이터를 만든다.
    """
    out: Dict[str, Any] = {
        "current_price_str": _format_price(
            financial.get("current_price") if financial else None,
            str((financial or {}).get("currency") or "KRW"),
        ),
        "band_low_str": "N/A",
        "band_high_str": "N/A",
        "band_position": None,        # -1.0 ~ +1.0 (밴드 하단=-1, 상단=+1)
        "diff_low_pct": None,
        "diff_high_pct": None,
        "method": str((band or {}).get("method") or "unavailable"),
    }
    if not band:
        return out

    currency = str((financial or {}).get("currency") or "KRW")
    band_low = band.get("band_low")
    band_high = band.get("band_high")
    out["band_low_str"] = _format_price(band_low, currency)
    out["band_high_str"] = _format_price(band_high, currency)

    price = (financial or {}).get("current_price")
    if (
        isinstance(price, (int, float))
        and isinstance(band_low, (int, float))
        and isinstance(band_high, (int, float))
        and band_high > band_low
    ):
        # 밴드 안에서의 상대 위치 (-1: 하단, +1: 상단)
        mid = (band_low + band_high) / 2.0
        half = (band_high - band_low) / 2.0
        if half > 0:
            out["band_position"] = round((float(price) - mid) / half, 3)
        if band_low != 0:
            out["diff_low_pct"] = round((float(price) - band_low) / band_low * 100.0, 2)
        if band_high != 0:
            out["diff_high_pct"] = round((float(price) - band_high) / band_high * 100.0, 2)
    return out


# -----------------------------------------------------------------------------
# FinancialSummary class
# -----------------------------------------------------------------------------


class FinancialSummary:
    """재무 요약 패널 컴포넌트."""

    def __init__(self, *, columns_per_row: int = 3) -> None:
        if columns_per_row not in (2, 3, 6):
            raise ValueError("columns_per_row 는 2/3/6 중 하나여야 합니다.")
        self._columns_per_row = columns_per_row

    # ------------------------------------------------------------------ pure
    @staticmethod
    def build_metrics(
        financial: Dict[str, Any],
        band: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, str, str]]:
        return format_metric_rows(financial, band)

    @staticmethod
    def build_band_summary(
        financial: Dict[str, Any], band: Dict[str, Any]
    ) -> Dict[str, Any]:
        return build_band_summary(financial, band)

    # ------------------------------------------------------------------ render
    def render(
        self,
        financial: Dict[str, Any],
        band: Optional[Dict[str, Any]] = None,
        *,
        title: Optional[str] = "재무 요약",
    ) -> None:
        try:
            import streamlit as st  # type: ignore
        except ImportError:  # pragma: no cover
            _LOGGER.error("streamlit 미설치")
            return

        if title:
            st.markdown(f"#### {title}")

        metrics = self.build_metrics(financial or {}, band or {})
        # st.metric 을 columns_per_row 단위로 그룹핑.
        for i in range(0, len(metrics), self._columns_per_row):
            chunk = metrics[i : i + self._columns_per_row]
            cols = st.columns(len(chunk))
            for col, (label, value, helper) in zip(cols, chunk):
                with col:
                    st.metric(label=label, value=value, help=helper)

        band_summary = self.build_band_summary(financial or {}, band or {})
        if band and band.get("band_low") is not None:
            with st.container():
                st.caption(
                    f"펀더멘털 밴드: {band_summary['band_low_str']} ~ {band_summary['band_high_str']} "
                    f"(산출방법: {band_summary['method']})"
                )
                if band_summary["diff_low_pct"] is not None:
                    st.caption(
                        f"현재가 vs 밴드 하단: {band_summary['diff_low_pct']:+.2f}% / "
                        f"vs 밴드 상단: {band_summary['diff_high_pct']:+.2f}%"
                    )
        else:
            st.caption("펀더멘털 밴드: 산출 불가 (재무 데이터 부족)")
