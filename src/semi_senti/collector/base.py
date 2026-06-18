"""수집기 공통 추상 클래스 (`BaseCollector`).

본 모듈은 PRD §F-1.3 "SQLite 캐싱 및 중복 호출 방지" 요건을 모든 수집기가
일관되게 구현하도록 다음 두 메서드를 표준화한다.

- ``_is_cache_fresh(...)``     : 캐시 TTL 유효 여부 판단
- ``_safe_call_api(...)``      : API 실패 시 캐시 폴백 처리(F-1.3.3)

또한 ``stocks`` 외래키 위반을 사전에 방지하기 위해 ``ensure_stock``
헬퍼를 두어 각 수집기가 호출 전 자동으로 종목을 upsert 하도록 한다.
"""

from __future__ import annotations

import logging
from abc import ABC
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Optional, TypeVar

from ..config import Settings, get_settings
from ..db import DBControl

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class CollectorError(RuntimeError):
    """수집기 공통 도메인 예외."""


class BaseCollector(ABC):
    """모든 수집기의 공통 부모.

    Parameters
    ----------
    db:
        외부에서 주입된 ``DBControl`` 인스턴스. ``None`` 이면 매 호출마다
        새로 열고 닫는 짧은 컨텍스트로 동작한다 (CLI 사용 등 단발성 케이스).
    settings:
        주입된 설정. ``None`` 이면 환경변수 스냅샷에서 빌드.
    """

    source_name: str = "base"  # 자식 클래스에서 'dart' / 'yfinance' / 'naver_news' 등으로 override

    def __init__(
        self,
        db: Optional[DBControl] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None
        self._settings: Settings = settings or get_settings()

    # ---------------------------------------------------------------------
    # DB lifecycle
    # ---------------------------------------------------------------------
    @property
    def settings(self) -> Settings:
        return self._settings

    def db(self) -> DBControl:
        """현재 사용 중인 DB 핸들을 반환한다 (없으면 새로 생성하여 보관)."""
        if self._db is None:
            self._db = DBControl()
            self._db.connect()
        else:
            self._db.connect()
        return self._db

    def close(self) -> None:
        """본 수집기가 소유한 DB 만 닫는다. 외부 주입된 핸들은 건드리지 않는다."""
        if self._owns_db and self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self) -> "BaseCollector":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---------------------------------------------------------------------
    # Stocks upsert helper (FK 위반 사전 차단)
    # ---------------------------------------------------------------------
    def ensure_stock(
        self,
        stock_code: str,
        name: Optional[str] = None,
        market: Optional[str] = None,
    ) -> None:
        """``stocks`` 테이블에 종목이 없으면 자동으로 등록한다.

        외래 키(`financials.stock_code` / `news.stock_code`) 위반을 사전 차단.
        """
        if not stock_code:
            raise CollectorError("ensure_stock: stock_code 는 필수입니다.")
        # 이미 등록된 종목인데 name 이 명시되지 않았으면 기존 종목명을 보존한다.
        if (not name or name == stock_code) and self.db().fetch_one(
            "SELECT 1 FROM stocks WHERE stock_code = %s", (stock_code,)
        ):
            return
        data = {"stock_code": stock_code, "name": name or stock_code}
        if market:
            data["market"] = market
        self.db().upsert("stocks", data, conflict_columns=["stock_code"])

    # ---------------------------------------------------------------------
    # TTL helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
        """SQLite 의 ``datetime('now')`` 또는 ISO 문자열을 파싱."""
        if not value:
            return None
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                # SQLite 기본 포맷: 'YYYY-MM-DD HH:MM:SS' (UTC). 'T' 구분자도 허용.
                dt = datetime.fromisoformat(str(value).replace("T", " ").split(".")[0])
            except (ValueError, AttributeError, TypeError):
                return None
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    @classmethod
    def _is_cache_fresh(
        cls,
        cached_at: Optional[str],
        ttl: timedelta,
        *,
        now: Optional[datetime] = None,
    ) -> bool:
        """캐시 신선도 판단.

        Parameters
        ----------
        cached_at:
            DB 에 저장된 수집 시각 문자열.
        ttl:
            허용 가능한 캐시 유효 기간.
        """
        cached_dt = cls._parse_iso_datetime(cached_at)
        if cached_dt is None:
            return False
        now = now or datetime.utcnow()
        return (now - cached_dt) <= ttl

    # ---------------------------------------------------------------------
    # API call with cache fallback (F-1.3.3)
    # ---------------------------------------------------------------------
    def _safe_call_api(
        self,
        api_callable: Callable[[], T],
        *,
        fallback_callable: Optional[Callable[[], T]] = None,
        operation_name: str = "external_api",
    ) -> T:
        """API 호출을 try/except 로 감싸고 실패 시 폴백을 시도한다.

        Parameters
        ----------
        api_callable:
            실제 외부 API 를 호출하는 무인자 콜러블.
        fallback_callable:
            API 가 실패했을 때 캐시에서 데이터를 끌어오는 콜러블.
            ``None`` 이면 그대로 예외 전파.
        operation_name:
            로깅용 작업명.

        Raises
        ------
        CollectorError:
            API 와 폴백 모두 실패한 경우.
        """
        try:
            return api_callable()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("%s 호출 실패: %s", operation_name, exc)
            if fallback_callable is None:
                raise CollectorError(f"{operation_name} 실패 (폴백 미정): {exc}") from exc
            try:
                result = fallback_callable()
                _LOGGER.info("%s: 캐시 폴백 사용", operation_name)
                return result
            except Exception as fb_exc:  # pylint: disable=broad-except
                raise CollectorError(
                    f"{operation_name}: API/폴백 모두 실패 ({exc} / {fb_exc})"
                ) from fb_exc

    # ---------------------------------------------------------------------
    # Helper: 시간/날짜 포맷 통일
    # ---------------------------------------------------------------------
    @staticmethod
    def now_iso() -> str:
        """UTC 기준 ISO 포맷 문자열 (DB 저장용)."""
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def merge_dict(*dicts: Mapping[str, Any]) -> dict:
        """여러 dict 를 뒤쪽 값 우선으로 병합. ``None`` 값은 무시."""
        merged: dict = {}
        for d in dicts:
            if not d:
                continue
            for k, v in d.items():
                if v is None:
                    continue
                merged[k] = v
        return merged
