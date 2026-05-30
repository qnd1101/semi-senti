"""분석 종목 관리 (T-046, F-6.1.1, UC-06).

> "분석 대상 종목 목록을 추가·수정·삭제할 수 있는 관리 인터페이스를 제공한다."

본 모듈은 종목 코드 유효성 검증(pykrx) 후 ``stocks`` 테이블에 적재한다.
- 등록 시 pykrx 로 OHLCV 존재 여부 확인 (UC-06 §E1).
- 삭제는 외래 키 ``ON DELETE CASCADE`` 로 관련 데이터까지 정리된다.
- 비활성화(soft delete) 도 별도 메서드로 제공.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl, DBControlError

_LOGGER = logging.getLogger(__name__)


_STOCK_CODE_PATTERN = re.compile(r"^\d{6}$")


class StockAdminError(RuntimeError):
    """관리자 작업 실패 도메인 예외."""


@dataclass
class StockValidationResult:
    """pykrx 검증 결과."""

    is_valid: bool
    yahoo_symbol: str
    error: Optional[str] = None
    info: Optional[Dict[str, Any]] = None


class StockAdmin:
    """``stocks`` 테이블 관리 + pykrx 검증.

    - 종목 코드 형식: 한국 6자리 숫자만 허용.
    - 시장 구분: KOSPI / KOSDAQ.
    """

    SUPPORTED_MARKETS = ("KOSPI", "KOSDAQ")

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

    def __enter__(self) -> "StockAdmin":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ validation
    @staticmethod
    def normalize_market(market: str) -> str:
        if not market:
            raise StockAdminError("market 은 필수입니다.")
        upper = market.strip().upper()
        if upper not in StockAdmin.SUPPORTED_MARKETS:
            raise StockAdminError(
                f"지원하지 않는 market: {market!r} (KOSPI/KOSDAQ 만 허용)"
            )
        return upper

    @staticmethod
    def validate_stock_code(stock_code: str) -> str:
        """6자리 숫자 검증 후 정규화 반환."""
        if not stock_code:
            raise StockAdminError("stock_code 는 필수입니다.")
        cleaned = stock_code.strip()
        if not _STOCK_CODE_PATTERN.match(cleaned):
            raise StockAdminError(
                f"유효하지 않은 종목 코드: {stock_code!r} (6자리 숫자만 허용)"
            )
        return cleaned

    def validate_with_yfinance(
        self, stock_code: str, market: str = "KOSPI"
    ) -> StockValidationResult:
        """yfinance 로 종목 유효성 확인 (UC-06)."""
        normalized_code = self.validate_stock_code(stock_code)
        normalized_market = self.normalize_market(market)
        yahoo_symbol = f"{normalized_code}.KS"
        if normalized_market == "KOSDAQ":
            yahoo_symbol = f"{normalized_code}.KQ"

        from ..collector.market_data import validate_stock_code as validate_yf

        ok, err = validate_yf(normalized_code, market=normalized_market)
        if not ok:
            return StockValidationResult(
                is_valid=False,
                yahoo_symbol=yahoo_symbol,
                error=err or "yfinance 검증 실패",
            )
        return StockValidationResult(is_valid=True, yahoo_symbol=yahoo_symbol)

    # ------------------------------------------------------------------ CRUD
    def list_stocks(self, *, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """종목 목록 조회 (관리 화면용)."""
        sql = (
            "SELECT stock_code, name, market, is_active, created_at, updated_at "
            "FROM stocks "
        )
        params: tuple = ()
        if not include_inactive:
            sql += "WHERE is_active = 1 "
        sql += "ORDER BY name ASC"
        try:
            return self.db().fetch_all(sql, params)
        except DBControlError as exc:
            _LOGGER.warning("list_stocks 실패: %s", exc)
            return []

    def add_stock(
        self,
        *,
        stock_code: str,
        name: str,
        market: str = "KOSPI",
        validate_with_yfinance: bool = True,
    ) -> Dict[str, Any]:
        """신규 종목 등록.

        - ``validate_with_yfinance=True`` 일 때 yfinance 로 ticker 유효성 확인.
        - 동일 ``stock_code`` 가 비활성 상태면 재활성화한다.
        """
        normalized_code = self.validate_stock_code(stock_code)
        normalized_market = self.normalize_market(market)
        if not name or not name.strip():
            raise StockAdminError("name 은 필수입니다.")

        if validate_with_yfinance:
            check = self.validate_with_yfinance(normalized_code, normalized_market)
            if not check.is_valid:
                raise StockAdminError(
                    f"yfinance 검증 실패 ({check.yahoo_symbol}): {check.error}"
                )

        try:
            self.db().upsert(
                "stocks",
                {
                    "stock_code": normalized_code,
                    "name": name.strip(),
                    "market": normalized_market,
                    "is_active": 1,
                    "updated_at": _now(),
                },
                conflict_columns=["stock_code"],
                update_columns=["name", "market", "is_active", "updated_at"],
            )
        except DBControlError as exc:
            raise StockAdminError(f"종목 등록 실패: {exc}") from exc

        row = self.db().fetch_one(
            "SELECT stock_code, name, market, is_active FROM stocks WHERE stock_code = ?",
            (normalized_code,),
        )
        _LOGGER.info("종목 등록: %s (%s)", name, normalized_code)
        return row or {}

    def update_stock(
        self,
        *,
        stock_code: str,
        name: Optional[str] = None,
        market: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """기존 종목의 메타 정보를 갱신한다."""
        normalized_code = self.validate_stock_code(stock_code)
        data: Dict[str, Any] = {}
        if name is not None:
            if not name.strip():
                raise StockAdminError("name 은 빈 문자열일 수 없습니다.")
            data["name"] = name.strip()
        if market is not None:
            data["market"] = self.normalize_market(market)
        if is_active is not None:
            data["is_active"] = 1 if is_active else 0
        if not data:
            raise StockAdminError("update 대상 필드가 없습니다.")
        data["updated_at"] = _now()

        try:
            affected = self.db().update(
                "stocks", data, where="stock_code = ?", where_params=(normalized_code,)
            )
        except DBControlError as exc:
            raise StockAdminError(f"종목 갱신 실패: {exc}") from exc
        if affected == 0:
            raise StockAdminError(f"존재하지 않는 종목 코드: {normalized_code}")
        _LOGGER.info("종목 갱신: %s — %s", normalized_code, list(data.keys()))
        return int(affected)

    def deactivate_stock(self, stock_code: str) -> int:
        """soft delete: ``is_active=0`` 으로 표시. 데이터 보존."""
        return self.update_stock(stock_code=stock_code, is_active=False)

    def delete_stock(self, stock_code: str, *, cascade: bool = True) -> int:
        """hard delete: ``stocks`` row 삭제 (관련 데이터는 FK CASCADE).

        - ``cascade=False`` 시에는 deactivate 만 수행하여 안전을 우선.
        """
        normalized_code = self.validate_stock_code(stock_code)
        if not cascade:
            return self.deactivate_stock(normalized_code)
        try:
            affected = self.db().delete(
                "stocks", where="stock_code = ?", where_params=(normalized_code,)
            )
        except DBControlError as exc:
            raise StockAdminError(f"종목 삭제 실패: {exc}") from exc
        if affected == 0:
            raise StockAdminError(f"존재하지 않는 종목 코드: {normalized_code}")
        _LOGGER.warning("종목 hard-delete: %s (CASCADE)", normalized_code)
        return int(affected)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
