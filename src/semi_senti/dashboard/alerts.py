"""대시보드 경고 배너 (T-039, F-1.3.3, UC-01 §E1).

> "API 오류·캐시 폴백 시 경고 배너 표시 구현 — 'N시간 전 데이터 기준' 안내"

본 모듈은 ``DataProvider.compute_stale_status`` 의 결과(``StaleStatus``)를
입력받아 사용자에게 노출할 경고 메시지를 빌드하고 Streamlit 으로 렌더링한다.

설계 원칙
---------
- *순수 메시지 빌더*( ``build_stale_message`` )와 *Streamlit 렌더러*
  ( ``render_alert_banner`` )를 분리.
- 경고 레벨 구분: ``info`` < ``warning`` < ``error``.
- ``error`` 일 때만 사용자 작업 흐름이 위험하므로 빨간 배너로 강조.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .data_provider import StaleStatus

_LOGGER = logging.getLogger(__name__)


# 임계 시간(시간 단위) — 그 이상이면 등급 상향.
_LEVEL_WARNING_HOURS = 6.0
_LEVEL_ERROR_HOURS = 24.0


def build_stale_message(stale: StaleStatus) -> Dict[str, Any]:
    """``StaleStatus`` 를 화면 메시지/등급 dict 로 변환.

    Returns
    -------
    dict
        ``{"level": "info"|"warning"|"error", "message": str, "show": bool}``
    """
    if stale is None:
        return {"level": "info", "message": "", "show": False}

    if not stale.is_stale and stale.last_updated:
        # 정상 신선도. 별도 알림 노출 X.
        return {"level": "info", "message": "", "show": False}

    # 기본 메시지
    if stale.message:
        message = stale.message
    elif stale.hours_old is not None:
        message = (
            f"외부 API 지연 또는 캐시 폴백 상태입니다. 약 {stale.hours_old:.1f}시간 전 데이터 기준으로 표시됩니다."
        )
    else:
        message = "외부 API 데이터 갱신 시각을 확인할 수 없습니다."

    # 레벨 결정
    hours = stale.hours_old or 0.0
    if hours >= _LEVEL_ERROR_HOURS or stale.last_updated is None:
        level = "error"
    elif hours >= _LEVEL_WARNING_HOURS:
        level = "warning"
    else:
        level = "info"

    if stale.last_updated:
        message += f"\n(최종 갱신: {stale.last_updated} UTC)"
    return {"level": level, "message": message, "show": True}


def render_alert_banner(stale: Optional[StaleStatus]) -> None:
    """Streamlit 화면 상단에 경고 배너를 렌더링한다.

    - ``stale`` 이 ``None`` 이거나 정상 신선도이면 아무것도 그리지 않는다.
    """
    try:
        import streamlit as st  # type: ignore
    except ImportError:  # pragma: no cover
        _LOGGER.error("streamlit 미설치")
        return

    if stale is None:
        return

    payload = build_stale_message(stale)
    if not payload.get("show"):
        return

    level = payload.get("level", "warning")
    message = payload.get("message", "")
    if level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)


def render_error_banner(error_message: str, *, level: str = "error") -> None:
    """예외 발생 시 사용할 일반 오류 배너 (UC-01 §E2)."""
    try:
        import streamlit as st  # type: ignore
    except ImportError:  # pragma: no cover
        _LOGGER.error("streamlit 미설치")
        return
    if not error_message:
        return
    if level == "warning":
        st.warning(error_message)
    elif level == "info":
        st.info(error_message)
    else:
        st.error(error_message)
