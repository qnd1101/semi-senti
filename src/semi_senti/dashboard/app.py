"""Streamlit 대시보드 메인 진입점 — ``ViewClass``.

Tasks 매핑
----------
- **T-037**: ``ViewClass`` 메인 레이아웃 (1화면 집중 원칙)
- **T-038**: 종목 선택 드롭다운 + 로딩 스피너
- **T-034**: 5분 interval 자동 갱신 (감성 게이지 포함)
- **T-039**: API 오류·캐시 폴백 시 경고 배너 (alerts 모듈 위임)

실행 방법
---------
``streamlit run src/semi_senti/dashboard/app.py`` 또는
``python -m semi_senti dashboard``.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# ``streamlit run .../app.py`` 는 패키지 컨텍스트 없이 실행되므로 절대 import 사용.
from semi_senti.config import get_settings
from semi_senti.dashboard.alerts import render_alert_banner, render_error_banner
from semi_senti.dashboard.chart import SignalChart
from semi_senti.dashboard.cycle_panel import render_cycle_panel
from semi_senti.dashboard.data_provider import DashboardSnapshot, DataProvider
from semi_senti.dashboard.financial_panel import FinancialSummary
from semi_senti.dashboard.sentiment_gauge import SentimentGauge
from semi_senti.engine import CycleAnalyzer

_LOGGER = logging.getLogger(__name__)


# 자동 갱신 주기 기본값 (초). PRD §F-4.2.4 참고.
_AUTO_REFRESH_SECONDS = 300


def _safe_import_streamlit():
    """Streamlit 미설치 환경에서도 모듈 import 가 깨지지 않도록 lazy import."""
    try:
        import streamlit as st  # type: ignore

        return st
    except ImportError:  # pragma: no cover - streamlit 미설치 환경
        return None


# -----------------------------------------------------------------------------
# ViewClass (T-037)
# -----------------------------------------------------------------------------


class ViewClass:
    """반도체 감성 분석 대시보드의 최상위 컨테이너.

    Parameters
    ----------
    refresh_interval_seconds:
        자동 갱신 주기. T-034 의 5분(300초) 기본값.
    candle_limit:
        차트에 표시할 최근 거래일 수 (기본 180일).
    signal_limit:
        차트에 표시할 시그널 마커 최대 개수.
    """

    def __init__(
        self,
        *,
        refresh_interval_seconds: int = _AUTO_REFRESH_SECONDS,
        candle_limit: int = 180,
        signal_limit: int = 60,
    ) -> None:
        self._refresh_interval_seconds = max(30, int(refresh_interval_seconds))
        self._candle_limit = max(30, int(candle_limit))
        self._signal_limit = max(5, int(signal_limit))
        self._chart = SignalChart(height=460)
        self._gauge = SentimentGauge(refresh_interval_seconds=self._refresh_interval_seconds)
        self._financial = FinancialSummary(columns_per_row=3)

    # ------------------------------------------------------------------ entry
    def run(self) -> None:
        """Streamlit 앱 진입점."""
        st = _safe_import_streamlit()
        if st is None:
            print("[ERROR] streamlit 이 설치되어 있지 않습니다. `pip install streamlit` 후 다시 실행하세요.")
            return

        self._configure_page(st)
        self._render_header(st)

        # 페이지 라우팅: 'main' (기본) | 'admin' (Phase 4-3)
        page = self._render_page_switch(st)
        if page == "admin":
            from semi_senti.dashboard.admin_page import render_admin_page

            render_admin_page()
            return

        provider = DataProvider()
        try:
            stocks = provider.list_active_stocks()
            selected = self._render_sidebar(st, stocks)
            if not selected:
                st.info("사이드바에서 분석할 종목을 선택해 주세요.")
                return

            stock_code = selected["stock_code"]
            stock_name = selected["name"]

            # T-038: 데이터 로딩 스피너 (UC-01 시나리오)
            with st.spinner(f"'{stock_name}' 분석 데이터를 불러오는 중..."):
                snapshot = provider.get_snapshot(
                    stock_code,
                    candle_limit=self._candle_limit,
                    signal_limit=self._signal_limit,
                )

            self._render_layout(st, snapshot)
        except Exception as exc:  # pylint: disable=broad-except
            # UC-01 §E2 — DB 접근 오류 등 광범위 예외 안내.
            _LOGGER.exception("대시보드 렌더링 실패")
            render_error_banner(
                f"일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요. ({exc})"
            )
        finally:
            try:
                provider.close()
            except Exception:  # pylint: disable=broad-except
                pass

        # T-034: 자동 갱신은 마지막에 트리거하여 위 렌더링 후 N초 뒤 rerun.
        self._schedule_auto_refresh(st)

    # ------------------------------------------------------------------ page
    def _configure_page(self, st) -> None:
        try:
            st.set_page_config(
                page_title="Semi Senti — 반도체 감성 분석 대시보드",
                page_icon=None,
                layout="wide",
                initial_sidebar_state="expanded",
            )
        except Exception as exc:  # pylint: disable=broad-except
            # set_page_config 는 한 번만 호출 가능 — 두 번째 호출 시 무시.
            _LOGGER.debug("set_page_config skipped: %s", exc)

    def _render_page_switch(self, st) -> str:
        """사이드바 라디오로 메인/관리자 페이지를 토글한다 (Phase 4-3)."""
        with st.sidebar:
            st.markdown("### 페이지")
            page = st.radio(
                "View",
                options=["메인", "관리자"],
                index=0,
                horizontal=True,
                key="page_selector",
                label_visibility="collapsed",
            )
            st.divider()
        return "admin" if page == "관리자" else "main"

    def _render_header(self, st) -> None:
        st.markdown(
            """
            <style>
              header[data-testid="stHeader"] { background: transparent; }
              .semi-senti-title { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
              .semi-senti-sub { color: #6B7280; font-size: 13px; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="semi-senti-title">Semi Senti</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="semi-senti-sub">반도체 특화 감성 + 펀더멘털 매매 시그널 대시보드</div>',
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------ sidebar (T-038)
    def _render_sidebar(
        self, st, stocks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """사이드바: 종목 선택 + 자동 갱신 설정 + 정보."""
        with st.sidebar:
            st.markdown("### 종목 선택")
            if not stocks:
                st.warning(
                    "분석 가능한 종목이 없습니다.\n"
                    "`semi_senti collect price --stock-code ... --stock-name ...` "
                    "명령으로 먼저 종목을 등록하세요."
                )
                return None

            # 드롭다운: 표시 라벨은 '종목명 (종목코드)' 형식.
            options = list(stocks)
            label_map = {
                f"{s.get('name') or s.get('stock_code')} ({s.get('stock_code')})": s
                for s in options
            }
            label = st.selectbox(
                "분석할 종목",
                options=list(label_map.keys()),
                index=0,
                key="stock_selector",
            )
            selected = label_map[label]

            st.divider()
            st.markdown("### 갱신 설정")
            auto_refresh = st.checkbox(
                "자동 갱신 사용 (T-034)", value=True, key="auto_refresh_enabled"
            )
            refresh_seconds = st.slider(
                "갱신 주기 (초)",
                min_value=60,
                max_value=900,
                value=self._refresh_interval_seconds,
                step=60,
                disabled=not auto_refresh,
                key="refresh_seconds",
            )
            # 위젯 key 로 session_state 가 자동 동기화됨 — 수동 대입 금지(Streamlit 제약).
            self._refresh_interval_seconds = int(refresh_seconds)

            st.divider()
            st.caption(f"렌더링 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.caption(
                "※ 본 화면은 투자 참고 자료이며, 매매 판단은 본인 책임입니다."
            )
        return selected

    # ------------------------------------------------------------------ main layout (T-037)
    def _render_layout(self, st, snapshot: DashboardSnapshot) -> None:
        # 1) 경고 배너 (T-039) — 최상단
        render_alert_banner(snapshot.stale)

        # 2) 종목 헤더
        title_col, info_col = st.columns([3, 2])
        with title_col:
            st.markdown(f"### {snapshot.stock_name} ({snapshot.stock_code})")
        with info_col:
            current_price = (snapshot.financial or {}).get("current_price")
            currency = (snapshot.financial or {}).get("currency", "KRW")
            if current_price is not None:
                price_text = (
                    f"{float(current_price):,.0f}원"
                    if currency == "KRW"
                    else f"{float(current_price):,.2f} {currency}"
                )
                st.markdown(
                    f"<div style='text-align: right; font-size: 18px; font-weight:700;'>{price_text}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"<div style='text-align: right;'>기준일 {snapshot.financial.get('record_date') or '-'}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("가격 데이터 없음")

        st.divider()

        # 3) 1화면 집중 레이아웃 (PRD §4.3) — 좌(차트) | 우(게이지)
        chart_col, side_col = st.columns([7, 5])

        with chart_col:
            st.markdown("#### 캔들 차트 + 시그널")
            self._chart.render(
                candles=snapshot.candles,
                signals=snapshot.signals,
                divergences=snapshot.divergences,
                band=snapshot.band,
                key=f"chart-{snapshot.stock_code}",
            )

        with side_col:
            self._gauge.render(snapshot.sentiment, title="감성 게이지")

        st.divider()

        # 4) 재무 요약 + 사이클 패널 (T-036, T-045)
        finance_col, cycle_col = st.columns([7, 5])
        with finance_col:
            self._financial.render(
                financial=snapshot.financial,
                band=snapshot.band,
                title="재무 요약",
            )
        with cycle_col:
            cycle_row = self._fetch_latest_cycle(snapshot.stock_code)
            render_cycle_panel(cycle_row)

    # ------------------------------------------------------------------ cycle helper
    @staticmethod
    def _fetch_latest_cycle(stock_code: str):
        """``cycle_scores`` 테이블에서 최신 1건을 반환 (없으면 None)."""
        try:
            with CycleAnalyzer() as ca:
                return ca.latest(stock_code)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("cycle 조회 실패: stock=%s err=%s", stock_code, exc)
            return None

    # ------------------------------------------------------------------ auto-refresh (T-034)
    def _schedule_auto_refresh(self, st) -> None:
        """Streamlit re-run 트리거 — 우선 ``streamlit-autorefresh`` 활용,
        미설치 시 ``time.sleep`` + ``st.rerun`` 폴백."""
        if not st.session_state.get("auto_refresh_enabled", True):
            return
        seconds = int(
            st.session_state.get("refresh_seconds", self._refresh_interval_seconds)
        )
        if seconds <= 0:
            return

        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore

            st_autorefresh(interval=seconds * 1000, key="semi-senti-auto-refresh")
            return
        except ImportError:
            pass

        # 폴백: 단순 sleep + rerun (UX 가 다소 거칠지만 필수 의존성 추가 회피)
        try:
            placeholder = st.empty()
            placeholder.caption(f"⏱ {seconds}초 후 자동 갱신")
            time.sleep(seconds)
            placeholder.empty()
            try:
                st.rerun()
            except AttributeError:
                # streamlit < 1.27
                st.experimental_rerun()  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("auto refresh fallback skipped: %s", exc)


# -----------------------------------------------------------------------------
# 모듈 함수 진입점 (CLI / streamlit run app.py 양쪽 지원)
# -----------------------------------------------------------------------------


def main() -> int:
    """대시보드 실행 진입점."""
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    ViewClass().run()
    return 0


# `streamlit run` 시 본 파일이 직접 실행됨 — top-level 에서 run() 호출.
if __name__ == "__main__":  # pragma: no cover - streamlit 런타임에서 호출
    main()
