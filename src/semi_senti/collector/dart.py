"""Open DART 재무제표 수집 모듈 (T-005, T-006, T-009).

> "Open DART API를 통해 반도체 종목의 매출액·영업이익·PER·PBR·EPS 등
>  재무제표 정보를 수집한다." — PRD F-1.1.1

지원 엔드포인트
----------------
- ``fnlttSinglAcnt.json``  : 단일회사 주요 계정 (매출액·영업이익 등)
- ``fnlttSinglIndx.json``  : 단일회사 주요 재무 지표 (PER·PBR·EPS 등)

설계
----
- DART 는 종목코드(``stock_code``, 6자리) 대신 자체 corp_code(8자리) 를 사용한다.
  본 모듈은 호출자가 corp_code 를 모를 수 있다는 가정 하에, ``stocks``
  테이블에 ``corp_code`` 컬럼이 없는 경우 외부 매핑 dict 를 받도록 한다.
  (corp_code 자동 다운로드/캐싱은 Phase 1-2 의 범위를 초과 → 후속 task 로 분리)
- 네트워크 호출은 ``requests`` 가 미설치된 환경에서도 import 시 깨지지 않도록
  lazy import.
- API 키가 없을 때는 ``CollectorError`` 를 명시적으로 발생시켜 호출자가
  즉시 인지할 수 있도록 한다 (.env 키 누락 케이스).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Mapping, Optional

from .base import BaseCollector, CollectorError
from .normalizer import DataNormalizer

_LOGGER = logging.getLogger(__name__)

# DART 응답의 account_nm → financials 컬럼 매핑.
_ACCOUNT_NAME_MAP: Dict[str, str] = {
    "매출액": "revenue",
    "수익(매출액)": "revenue",
    "영업이익": "operating_profit",
    "영업이익(손실)": "operating_profit",
}

# DART 주요지표 응답의 idx_nm 매칭. (실제 API 는 다양한 별칭을 사용)
_INDX_NAME_MAP: Dict[str, str] = {
    "주당순이익": "eps",
    "EPS": "eps",
    "주가수익비율": "per",
    "PER": "per",
    "주가순자산비율": "pbr",
    "PBR": "pbr",
}


class DartFinancialCollector(BaseCollector):
    """DART API 재무제표 수집기."""

    source_name = "dart"

    # ------------------------------------------------------------------ helpers
    def _require_api_key(self) -> str:
        key = self.settings.open_dart_api_key
        if not key:
            raise CollectorError(
                "OPEN_DART_API_KEY 가 설정되지 않았습니다. .env 파일을 확인하세요."
            )
        return key

    def _http_get_json(self, endpoint: str, params: Mapping[str, Any]) -> dict:
        """공통 HTTP GET → JSON 디코드. ``requests`` 가 없으면 명확한 에러."""
        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CollectorError(
                "'requests' 패키지가 필요합니다. `pip install -r requirements.txt` 를 실행하세요."
            ) from exc

        url = f"{self.settings.dart_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=self.settings.http_timeout_seconds,
                headers={"User-Agent": "SemiSenti/0.1 (+https://example.local)"},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CollectorError(f"DART HTTP 실패 ({url}): {exc}") from exc

        try:
            payload = resp.json()
        except ValueError as exc:
            raise CollectorError(f"DART 응답 JSON 파싱 실패: {exc}") from exc

        status = str(payload.get("status", ""))
        if status and status != "000":
            # DART 응답 status: '013' = 조회된 데이터 없음, '020' = 사용한도 초과 등
            raise CollectorError(
                f"DART API 오류 status={status}, message={payload.get('message')}"
            )
        return payload

    # ------------------------------------------------------------------ public
    def fetch_single_company_account(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: Optional[str] = None,
    ) -> list:
        """``fnlttSinglAcnt.json`` 호출. raw ``list`` 반환."""
        params = {
            "crtfc_key": self._require_api_key(),
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code or self.settings.dart_default_reprt_code,
        }
        payload = self._http_get_json("fnlttSinglAcnt.json", params)
        return list(payload.get("list", []))

    def fetch_single_company_index(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: Optional[str] = None,
        idx_cl_code: str = "M210000",
    ) -> list:
        """``fnlttSinglIndx.json`` 호출 (수익성/안정성/성장성/활동성 지표)."""
        params = {
            "crtfc_key": self._require_api_key(),
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code or self.settings.dart_default_reprt_code,
            "idx_cl_code": idx_cl_code,
        }
        payload = self._http_get_json("fnlttSinglIndx.json", params)
        return list(payload.get("list", []))

    # ------------------------------------------------------------------ parse
    @staticmethod
    def parse_account_rows(rows: list) -> Dict[str, Optional[float]]:
        """fnlttSinglAcnt.json 응답에서 매출액·영업이익 추출."""
        out: Dict[str, Optional[float]] = {"revenue": None, "operating_profit": None}
        for row in rows or []:
            name = (row.get("account_nm") or "").strip()
            target = _ACCOUNT_NAME_MAP.get(name)
            if not target:
                continue
            # 최근 분기 금액: 'thstrm_amount' / 'thstrm_add_amount' (누적)
            amount = row.get("thstrm_amount") or row.get("thstrm_add_amount")
            out[target] = DataNormalizer.to_float(amount)
        return out

    @staticmethod
    def parse_index_rows(rows: list) -> Dict[str, Optional[float]]:
        """fnlttSinglIndx.json 응답에서 PER·PBR·EPS 추출."""
        out: Dict[str, Optional[float]] = {"per": None, "pbr": None, "eps": None}
        for row in rows or []:
            name = (row.get("idx_nm") or "").strip().upper().replace(" ", "")
            for key, target in _INDX_NAME_MAP.items():
                if key.upper().replace(" ", "") in name:
                    out[target] = DataNormalizer.to_float(row.get("idx_val"))
                    break
        return out

    # ------------------------------------------------------------------ orchestration (T-009)
    def collect_and_store(
        self,
        stock_code: str,
        corp_code: str,
        bsns_year: Optional[str] = None,
        *,
        stock_name: Optional[str] = None,
        record_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """DART 호출 → 정규화 → ``financials`` UPSERT 까지 한 번에 처리.

        Returns
        -------
        dict
            적재된 정규화 레코드.

        Raises
        ------
        CollectorError
            API 또는 DB 단계 실패 시 (캐시 폴백 후에도 실패한 경우).
        """
        if not stock_code or not corp_code:
            raise CollectorError("collect_and_store: stock_code/corp_code 는 필수입니다.")

        bsns_year = bsns_year or str(datetime.utcnow().year - 1)
        record_date = record_date or datetime.utcnow().strftime("%Y-%m-%d")

        def _api_call() -> Dict[str, Optional[float]]:
            accounts = self.parse_account_rows(
                self.fetch_single_company_account(corp_code, bsns_year)
            )
            indices = self.parse_index_rows(
                self.fetch_single_company_index(corp_code, bsns_year)
            )
            merged: Dict[str, Optional[float]] = {}
            merged.update(accounts)
            merged.update(indices)
            return merged

        def _fallback() -> Dict[str, Optional[float]]:
            row = self.db().fetch_one(
                "SELECT revenue, operating_profit, per, pbr, eps "
                "FROM financials WHERE stock_code = ? "
                "ORDER BY record_date DESC LIMIT 1",
                (stock_code,),
            )
            if not row:
                raise CollectorError(f"폴백 캐시 없음: {stock_code}")
            return row

        raw = self._safe_call_api(
            _api_call,
            fallback_callable=_fallback,
            operation_name=f"DART({stock_code}/{bsns_year})",
        )

        record = DataNormalizer.normalize_financial_record(
            stock_code=stock_code, record_date=record_date, raw=raw, currency="KRW"
        )
        self.ensure_stock(stock_code=stock_code, name=stock_name)
        # 주가 컬럼은 price 수집기가 담당 → 재무 필드만 갱신해 기존 OHLCV 를 보존한다.
        self.db().upsert(
            "financials",
            record,
            conflict_columns=["stock_code", "record_date"],
            update_columns=[
                "revenue",
                "operating_profit",
                "per",
                "pbr",
                "eps",
                "currency",
                "updated_at",
            ],
        )
        _LOGGER.info(
            "DART 적재 완료: stock=%s, date=%s, revenue=%s, op=%s, PER=%s",
            stock_code,
            record["record_date"],
            record.get("revenue"),
            record.get("operating_profit"),
            record.get("per"),
        )
        return record

    # ------------------------------------------------------------------ cache check
    def is_cache_fresh(self, stock_code: str) -> bool:
        """주어진 종목의 최신 ``financials`` 캐시가 TTL 내인지 확인."""
        row = self.db().fetch_one(
            "SELECT updated_at FROM financials WHERE stock_code = ? "
            "ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        if not row:
            return False
        ttl = timedelta(hours=self.settings.financial_cache_ttl_hours)
        return self._is_cache_fresh(row.get("updated_at"), ttl)
