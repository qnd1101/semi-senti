"""Streamlit 대시보드 계층 (Phase 3, F-4.1 ~ F-4.3).

본 패키지는 PRD §4.3 "1화면 집중 원칙" 을 따르는 메인 뷰
(:class:`ViewClass`) 와 그 내부 컴포넌트로 구성된다.

빠른 사용 예::

    from semi_senti.dashboard import ViewClass
    ViewClass().run()        # streamlit run 환경에서 호출

또는 CLI ::

    python -m semi_senti dashboard
"""

from .alerts import build_stale_message, render_alert_banner, render_error_banner
from .chart import (
    SignalChart,
    build_chart_options,
    build_divergence_markers,
    build_signal_markers,
)
from .cycle_panel import build_cycle_payload, render_cycle_panel
from .data_provider import (
    DashboardSnapshot,
    DataProvider,
    StaleStatus,
    classify_sentiment,
)
from .financial_panel import (
    FinancialSummary,
    build_band_summary,
    format_metric_rows,
)
from .sentiment_gauge import (
    SentimentGauge,
    build_gauge_payload,
    build_keyword_rows,
)

__all__ = [
    # data
    "DataProvider",
    "DashboardSnapshot",
    "StaleStatus",
    "classify_sentiment",
    # chart
    "SignalChart",
    "build_chart_options",
    "build_signal_markers",
    "build_divergence_markers",
    # gauge
    "SentimentGauge",
    "build_gauge_payload",
    "build_keyword_rows",
    # financial
    "FinancialSummary",
    "format_metric_rows",
    "build_band_summary",
    # cycle (Phase 4-2)
    "render_cycle_panel",
    "build_cycle_payload",
    # alerts
    "render_alert_banner",
    "render_error_banner",
    "build_stale_message",
]


def get_view_class():
    """ViewClass 지연 임포트 — Streamlit 미설치 환경에서도 패키지 import 가능."""
    from .app import ViewClass

    return ViewClass


# 호환 편의를 위해 패키지 레벨에서 ``ViewClass`` 도 노출 (lazy attribute).
def __getattr__(name: str):  # PEP 562
    if name == "ViewClass":
        return get_view_class()
    raise AttributeError(f"module 'semi_senti.dashboard' has no attribute '{name}'")
