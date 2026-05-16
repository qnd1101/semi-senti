"""결측치 처리 및 단위 통일 (T-008, F-1.1.3).

> "API 응답(JSON/XML)에서 필요 필드를 파싱하고, 결측치 처리 및
>  단위 통일(원/달러 등)을 수행한다." — PRD F-1.1.3

본 모듈은 외부 의존성 없이 순수 Python 으로 동작하여 테스트가 쉽다.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from typing import Any, Mapping, Optional

_LOGGER = logging.getLogger(__name__)

# DART 응답의 금액 문자열에는 쉼표·공백·괄호(음수) 가 섞여 있을 수 있다.
_RE_NUMBER_CLEAN = re.compile(r"[,\s]")
_RE_PARENS_NEGATIVE = re.compile(r"^\(([0-9.]+)\)$")

# 통화 변환 기본 환율 (참고용 - 실제로는 환율 API 가 별도 필요).
# Phase 1 단계에서는 한국 종목만 다루므로 KRW 기본 사용.
_DEFAULT_FX_TO_KRW = {
    "KRW": 1.0,
    "USD": 1300.0,  # placeholder; 실제 운영 시 외부 환율 API 로 갱신 권장.
}


class DataNormalizer:
    """수집된 raw 데이터를 ``financials`` 스키마에 맞게 정규화."""

    # ------------------------------------------------------------------ scalar
    @staticmethod
    def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """다양한 형태의 입력을 float 로 안전 변환.

        - ``None``, ``""``, ``"-"``, ``"NaN"``  → ``default``
        - ``"1,234"`` → 1234.0
        - ``"(1,000)"`` → -1000.0 (회계 음수 표기)
        - float/int 는 그대로 (NaN 인 경우 default)
        """
        if value is None:
            return default
        if isinstance(value, bool):
            # bool 은 int 의 하위 클래스 → 의도치 않은 변환 방지.
            return float(value)
        if isinstance(value, (int, float)):
            f = float(value)
            return default if math.isnan(f) else f
        if isinstance(value, str):
            s = value.strip()
            if not s or s in {"-", "—", "NaN", "nan", "N/A", "null", "None"}:
                return default
            # 음수 괄호 표기
            m = _RE_PARENS_NEGATIVE.match(s)
            if m:
                cleaned = _RE_NUMBER_CLEAN.sub("", m.group(1))
                try:
                    return -float(cleaned)
                except ValueError:
                    return default
            cleaned = _RE_NUMBER_CLEAN.sub("", s)
            try:
                f = float(cleaned)
                return default if math.isnan(f) else f
            except ValueError:
                return default
        # 그 외 타입은 안전하게 default
        return default

    @staticmethod
    def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        f = DataNormalizer.to_float(value, default=None)
        if f is None:
            return default
        try:
            return int(f)
        except (OverflowError, ValueError):
            return default

    @staticmethod
    def normalize_date(value: Any, default: Optional[str] = None) -> Optional[str]:
        """다양한 날짜 표기를 ``YYYY-MM-DD`` 로 통일."""
        if value is None or value == "":
            return default
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        s = str(value).strip()
        # 'YYYY-MM-DD HH:MM:SS' / 'YYYY-MM-DDTHH:MM:SS' → 앞 10자
        if len(s) >= 10 and (s[4] == "-" and s[7] == "-"):
            return s[:10]
        # 'YYYYMMDD'
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        try:
            return datetime.fromisoformat(s.split(".")[0]).strftime("%Y-%m-%d")
        except ValueError:
            return default

    # ------------------------------------------------------------------ unit
    @classmethod
    def to_krw(cls, amount: Optional[float], currency: str = "KRW") -> Optional[float]:
        """주어진 통화 금액을 KRW(원) 으로 환산."""
        if amount is None:
            return None
        rate = _DEFAULT_FX_TO_KRW.get((currency or "KRW").upper())
        if rate is None:
            _LOGGER.warning("알 수 없는 통화 %r → 환산 생략 (원본 금액 유지)", currency)
            return amount
        return amount * rate

    # ------------------------------------------------------------------ record
    @classmethod
    def normalize_financial_record(
        cls,
        stock_code: str,
        record_date: Any,
        raw: Mapping[str, Any],
        *,
        currency: str = "KRW",
    ) -> dict:
        """DART 등에서 받은 재무 필드를 ``financials`` 스키마 컬럼명/형식으로 변환.

        ``raw`` 는 다음 키를 임의 조합으로 가질 수 있다::

            revenue / operating_profit / per / pbr / eps
            open / high / low / close / volume

        존재하지 않거나 결측인 컬럼은 ``None`` 으로 채워 SQLite NULL 로 저장된다.
        """
        if not stock_code:
            raise ValueError("normalize_financial_record: stock_code 는 필수입니다.")

        date_str = cls.normalize_date(record_date)
        if date_str is None:
            raise ValueError(
                f"normalize_financial_record: record_date 파싱 실패 ({record_date!r})"
            )

        out: dict = {
            "stock_code": stock_code,
            "record_date": date_str,
            "open_price": cls.to_float(raw.get("open") or raw.get("open_price")),
            "high_price": cls.to_float(raw.get("high") or raw.get("high_price")),
            "low_price": cls.to_float(raw.get("low") or raw.get("low_price")),
            "close_price": cls.to_float(raw.get("close") or raw.get("close_price")),
            "volume": cls.to_int(raw.get("volume")),
            "revenue": cls.to_krw(cls.to_float(raw.get("revenue")), currency),
            "operating_profit": cls.to_krw(
                cls.to_float(raw.get("operating_profit")), currency
            ),
            "per": cls.to_float(raw.get("per")),
            "pbr": cls.to_float(raw.get("pbr")),
            "eps": cls.to_float(raw.get("eps")),
            "currency": "KRW",  # 환산 후 저장 단위는 항상 KRW.
        }
        return out
