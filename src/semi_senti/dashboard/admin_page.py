"""관리자 페이지 (T-046, T-047, F-6.1).

별도 Streamlit 페이지로 동작한다. 사용자는 ``ViewClass`` 의 사이드바 또는
URL 쿼리(`?page=admin`) 로 본 페이지를 호출한다.

설계
----
- 본 모듈은 *Streamlit 의존* 이지만, 비즈니스 로직(추가/수정/삭제, 수동 갱신)
  은 ``admin/`` 패키지에 두어 GUI 와 분리한다.
- 페이지 이동/탭 전환은 ``st.tabs`` 로 단순화.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..admin import StockAdmin, StockAdminError, SystemMonitor
from ..notifier import NotificationManager

_LOGGER = logging.getLogger(__name__)


def render_admin_page() -> None:
    """관리자 페이지 진입점."""
    try:
        import streamlit as st  # type: ignore
    except ImportError:  # pragma: no cover
        _LOGGER.error("streamlit 미설치")
        return

    st.markdown("## Semi Senti — 관리자 콘솔")
    st.caption("운영자 전용 화면 (UC-06 / UC-07)")

    tabs = st.tabs(["📦 종목 관리", "🩺 시스템 모니터링", "🚨 알림 이력"])
    with tabs[0]:
        _render_stock_admin(st)
    with tabs[1]:
        _render_system_monitor(st)
    with tabs[2]:
        _render_notification_history(st)


# -----------------------------------------------------------------------------
# Tab 1: 종목 관리 (T-046, UC-06)
# -----------------------------------------------------------------------------


def _render_stock_admin(st) -> None:
    st.markdown("### 종목 추가")
    with st.form(key="admin-add-stock"):
        col_code, col_name, col_market = st.columns([2, 3, 2])
        with col_code:
            stock_code = st.text_input("종목 코드 (6자리)", value="").strip()
        with col_name:
            stock_name = st.text_input("종목명", value="").strip()
        with col_market:
            market = st.selectbox(
                "시장", options=list(StockAdmin.SUPPORTED_MARKETS), index=0
            )
        validate = st.checkbox("yfinance 로 코드 유효성 검증", value=True)
        submitted = st.form_submit_button("등록")
        if submitted:
            if not stock_code or not stock_name:
                st.error("종목 코드와 종목명은 모두 필수입니다.")
            else:
                try:
                    with StockAdmin() as admin:
                        row = admin.add_stock(
                            stock_code=stock_code,
                            name=stock_name,
                            market=market,
                            validate_with_yfinance=validate,
                        )
                    st.success(f"등록 완료: {row.get('name')} ({row.get('stock_code')})")
                except StockAdminError as exc:
                    st.error(f"등록 실패: {exc}")

    st.divider()
    st.markdown("### 등록 종목 목록")

    show_inactive = st.toggle("비활성 종목 포함", value=False, key="admin-show-inactive")

    try:
        with StockAdmin() as admin:
            stocks = admin.list_stocks(include_inactive=show_inactive)
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"종목 조회 실패: {exc}")
        return

    if not stocks:
        st.info("등록된 종목이 없습니다.")
        return

    for stock in stocks:
        _render_stock_row(st, stock)


def _render_stock_row(st, stock: Dict[str, Any]) -> None:
    code = stock["stock_code"]
    is_active = bool(stock.get("is_active"))
    cols = st.columns([3, 2, 2, 2, 2])
    with cols[0]:
        active_badge = "🟢 활성" if is_active else "⚪ 비활성"
        st.markdown(f"**{stock.get('name')}** `({code})` · {active_badge}")
        st.caption(f"시장: {stock.get('market') or '-'} · 갱신: {stock.get('updated_at') or '-'}")
    with cols[1]:
        new_name = st.text_input(
            "종목명 수정", value=stock.get("name") or "", key=f"name-{code}"
        )
    with cols[2]:
        if st.button("저장", key=f"save-{code}", use_container_width=True):
            _safe_update(st, code, name=new_name)
    with cols[3]:
        if st.button(
            "비활성화" if is_active else "활성화",
            key=f"toggle-{code}",
            use_container_width=True,
        ):
            _safe_update(st, code, is_active=not is_active)
    with cols[4]:
        if st.button("삭제", key=f"delete-{code}", use_container_width=True, type="secondary"):
            _safe_delete(st, code)
    st.divider()


def _safe_update(st, stock_code: str, **fields) -> None:
    try:
        with StockAdmin() as admin:
            admin.update_stock(stock_code=stock_code, **fields)
        st.success(f"갱신 완료: {stock_code}")
        _trigger_rerun(st)
    except StockAdminError as exc:
        st.error(f"갱신 실패: {exc}")


def _safe_delete(st, stock_code: str) -> None:
    try:
        with StockAdmin() as admin:
            admin.delete_stock(stock_code=stock_code, cascade=True)
        st.success(f"삭제 완료: {stock_code} (CASCADE)")
        _trigger_rerun(st)
    except StockAdminError as exc:
        st.error(f"삭제 실패: {exc}")


def _trigger_rerun(st) -> None:
    try:
        st.rerun()
    except AttributeError:  # streamlit < 1.27
        st.experimental_rerun()  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# Tab 2: 시스템 모니터링 (T-047, UC-07)
# -----------------------------------------------------------------------------


def _render_system_monitor(st) -> None:
    st.markdown("### 수집·분석 상태")
    try:
        with SystemMonitor() as monitor:
            report = monitor.status_report()
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"상태 수집 실패: {exc}")
        return

    head_cols = st.columns(4)
    head_cols[0].metric("등록 종목", report.table_counts.get("stocks", 0))
    head_cols[1].metric("뉴스 누적", report.table_counts.get("news", 0))
    head_cols[2].metric("시그널 누적", report.table_counts.get("signals", 0))
    head_cols[3].metric(
        "미발송 알림", report.failed_notifications, help="status='FAILED' 카운트"
    )

    if report.warnings:
        with st.expander("경고 메시지"):
            for w in report.warnings:
                st.warning(w)

    if not report.stocks:
        st.info("등록된 종목이 없습니다. [종목 관리] 탭에서 먼저 등록하세요.")
        return

    st.dataframe(
        [
            {
                "종목": f"{s.name} ({s.stock_code})",
                "시장": s.market or "-",
                "활성": "Y" if s.is_active else "N",
                "최근 가격": s.last_price_at or "-",
                "최근 뉴스": s.last_news_at or "-",
                "뉴스 수": s.news_count,
                "최근 시그널": s.last_signal_at or "-",
                "시그널 수": s.signal_count,
                "최근 감성": s.last_sentiment_date or "-",
            }
            for s in report.stocks
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.markdown("### 수동 갱신")

    options = {f"{s.name} ({s.stock_code})": s for s in report.stocks}
    selected_label = st.selectbox(
        "갱신할 종목", list(options.keys()), key="admin-refresh-select"
    )
    selected = options[selected_label]

    market = st.selectbox(
        "시장",
        options=list(StockAdmin.SUPPORTED_MARKETS),
        index=0 if (selected.market or "KOSPI") == "KOSPI" else 1,
        key="admin-refresh-market",
    )
    news_query = st.text_input(
        "뉴스 검색 키워드 (비우면 뉴스 수집 생략)",
        value=selected.name,
        key="admin-refresh-news-query",
    )
    flags_col = st.columns(3)
    with flags_col[0]:
        run_sentiment = st.checkbox("감성 분석", value=True, key="admin-r-sentiment")
    with flags_col[1]:
        run_signal = st.checkbox("시그널 산출", value=True, key="admin-r-signal")
    with flags_col[2]:
        run_cycle = st.checkbox("사이클 분석", value=True, key="admin-r-cycle")

    if st.button("즉시 갱신", type="primary", key="admin-refresh-btn"):
        with st.spinner(f"{selected.name} 갱신 중..."):
            try:
                with SystemMonitor() as monitor:
                    result = monitor.manual_refresh(
                        stock_code=selected.stock_code,
                        market=market,
                        news_query=news_query or None,
                        run_signal=run_signal,
                        run_sentiment=run_sentiment,
                        run_cycle=run_cycle,
                    )
            except Exception as exc:  # pylint: disable=broad-except
                st.error(f"갱신 실패: {exc}")
                return

        if result["ok"]:
            st.success(f"갱신 완료 ({result['finished_at']})")
        else:
            st.warning(f"일부 단계 실패: {', '.join(result['errors'])}")
        st.json(result["steps"])


# -----------------------------------------------------------------------------
# Tab 3: 알림 이력
# -----------------------------------------------------------------------------


def _render_notification_history(st) -> None:
    st.markdown("### 발송 실패 이력")
    try:
        with NotificationManager() as nm:
            failed = nm.list_failed(limit=50)
            failed_count = nm.count_failed()
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"알림 이력 조회 실패: {exc}")
        return

    st.metric("미발송 알림", failed_count)
    if not failed:
        st.success("실패한 알림이 없습니다.")
        return

    st.dataframe(
        [
            {
                "ID": row["id"],
                "종목": row["stock_code"],
                "유형": row["event_type"],
                "재시도": row["retry_count"],
                "에러": row["last_error"],
                "발생": row["created_at"],
            }
            for row in failed
        ],
        use_container_width=True,
        hide_index=True,
    )
