"""Open DART 재무제표 수집 모듈 (T-005, T-006, T-009).

> "Open DART API를 통해 반도체 종목의 매출액·영업이익·PER·PBR·EPS 등
>  재무제표 정보를 수집한다." — PRD F-1.1.1

지원 엔드포인트
----------------
- ``fnlttSinglAcnt.json``     : 단일회사 주요 계정 (매출·영업이익·순이익·자본)
- ``fnlttSinglIndx.json``     : 단일회사 주요 재무 지표 (PER·PBR·EPS, 있을 때)
- ``stockTotqySttus.json``    : 주식 총수 → EPS/BPS 산출, 종가(yfinance)로 PER/PBR 보완

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
    "당기순이익(손실)": "net_income",
    "당기순이익": "net_income",
    "자본총계": "equity",
}

# 연결(CFS) 우선 — 별도/개별(OFS) 보다 상장사 시장 지표에 적합.
_FS_DIV_PRIORITY: Dict[str, int] = {"CFS": 0, "OFS": 1}

# DART 주요지표 응답의 idx_nm 매칭. (실제 API 는 다양한 별칭을 사용)
_INDX_NAME_MAP: Dict[str, str] = {
    "주당순이익": "eps",
    "EPS": "eps",
    "주가수익비율": "per",
    "PER": "per",
    "주가순자산비율": "pbr",
    "PBR": "pbr",
}

_IDX_CL_CODES = ("M210000", "M220000", "M230000", "M240000")


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

    def fetch_stock_totqy_sttus(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: Optional[str] = None,
    ) -> list:
        """``stockTotqySttus.json`` 호출 — 유통(보통) 주식 수."""
        params = {
            "crtfc_key": self._require_api_key(),
            "corp_code": corp_code,
            "bsns_year": str(bsns_year),
            "reprt_code": reprt_code or self.settings.dart_default_reprt_code,
        }
        payload = self._http_get_json("stockTotqySttus.json", params)
        return list(payload.get("list", []))

    def _fetch_merged_indices(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: Optional[str] = None,
    ) -> Dict[str, Optional[float]]:
        """수익성·안정성·성장성·활동성 지표 API 를 순회해 PER/PBR/EPS 를 병합."""
        merged: Dict[str, Optional[float]] = {"per": None, "pbr": None, "eps": None}
        for idx_cl_code in _IDX_CL_CODES:
            try:
                rows = self.fetch_single_company_index(
                    corp_code, bsns_year, reprt_code=reprt_code, idx_cl_code=idx_cl_code
                )
            except CollectorError:
                continue
            partial = self.parse_index_rows(rows)
            for key, value in partial.items():
                if value is not None:
                    merged[key] = value
        return merged

    # ------------------------------------------------------------------ parse
    @staticmethod
    def _account_fs_priority(row: Mapping[str, Any]) -> int:
        fs_div = (row.get("fs_div") or "").strip().upper()
        return _FS_DIV_PRIORITY.get(fs_div, 9)

    @classmethod
    def parse_account_rows(cls, rows: list) -> Dict[str, Optional[float]]:
        """fnlttSinglAcnt.json 응답에서 매출·이익·순이익·자본 추출 (연결 우선)."""
        fields = ("revenue", "operating_profit", "net_income", "equity")
        out: Dict[str, Optional[float]] = {name: None for name in fields}
        best: Dict[str, tuple] = {}
        for row in rows or []:
            name = (row.get("account_nm") or "").strip()
            target = _ACCOUNT_NAME_MAP.get(name)
            if not target:
                continue
            amount = row.get("thstrm_amount") or row.get("thstrm_add_amount")
            value = DataNormalizer.to_float(amount)
            if value is None:
                continue
            priority = cls._account_fs_priority(row)
            prev = best.get(target)
            if prev is None or priority < prev[0]:
                best[target] = (priority, value)
        for target, (_, value) in best.items():
            out[target] = value
        return out

    @staticmethod
    def parse_stock_totqy_rows(rows: list) -> Optional[float]:
        """stockTotqySttus.json 에서 PER/PBR 산출용 유통 주식 수(주)."""
        if not rows:
            return None
        preferred: Optional[float] = None
        fallback: Optional[float] = None
        for row in rows:
            se = (row.get("se") or "").strip()
            qty = DataNormalizer.to_float(row.get("distb_stock_co"))
            if qty is None or qty <= 0:
                continue
            if "보통주" in se:
                preferred = qty
            if fallback is None or qty > fallback:
                fallback = qty
        return preferred if preferred is not None else fallback

    @staticmethod
    def enrich_valuation_ratios(
        stock_code: str,
        data: Mapping[str, Optional[float]],
        *,
        close_price: Optional[float] = None,
    ) -> Dict[str, Optional[float]]:
        """순이익·자본·주식수·종가로 EPS/PER/PBR 을 보완한다 (API 미제공 시)."""
        out: Dict[str, Optional[float]] = {
            "eps": data.get("eps"),
            "per": data.get("per"),
            "pbr": data.get("pbr"),
        }
        shares = data.get("shares_outstanding")
        net_income = data.get("net_income")
        equity = data.get("equity")

        if out["eps"] is None and net_income is not None and shares and shares > 0:
            out["eps"] = net_income / shares

        bps: Optional[float] = None
        if equity is not None and shares and shares > 0:
            bps = equity / shares

        if close_price is None or close_price <= 0:
            return out

        eps = out["eps"]
        if out["per"] is None and eps is not None and eps > 0:
            out["per"] = close_price / eps
        if out["pbr"] is None and bps is not None and bps > 0:
            out["pbr"] = close_price / bps
        return out

    def _latest_close_price(self, stock_code: str) -> Optional[float]:
        """``financials`` 에 적재된 최신 종가 (price 수집기 결과)."""
        row = self.db().fetch_one(
            "SELECT close_price FROM financials WHERE stock_code = ? "
            "AND close_price IS NOT NULL ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        if not row:
            return None
        return DataNormalizer.to_float(row.get("close_price"))

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
            account_rows = self.fetch_single_company_account(corp_code, bsns_year)
            accounts = self.parse_account_rows(account_rows)
            indices = self._fetch_merged_indices(corp_code, bsns_year)

            shares: Optional[float] = None
            try:
                stock_rows = self.fetch_stock_totqy_sttus(corp_code, bsns_year)
                shares = self.parse_stock_totqy_rows(stock_rows)
            except CollectorError as exc:
                _LOGGER.debug("DART 주식총수 조회 스킵(%s): %s", stock_code, exc)

            valuation = self.enrich_valuation_ratios(
                stock_code,
                {
                    "eps": indices.get("eps"),
                    "per": indices.get("per"),
                    "pbr": indices.get("pbr"),
                    "net_income": accounts.get("net_income"),
                    "equity": accounts.get("equity"),
                    "shares_outstanding": shares,
                },
                close_price=self._latest_close_price(stock_code),
            )

            merged: Dict[str, Optional[float]] = {
                "revenue": accounts.get("revenue"),
                "operating_profit": accounts.get("operating_profit"),
                "eps": valuation.get("eps"),
                "per": valuation.get("per"),
                "pbr": valuation.get("pbr"),
            }
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
