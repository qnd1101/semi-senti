"""DART corp_code 조회·캐시 (stock_code 6자리 → corp_code 8자리)."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, Optional
from xml.etree import ElementTree

from ..config.settings import Settings, get_settings
from ..data.default_stocks import get_default_stock
from .base import CollectorError

_LOGGER = logging.getLogger(__name__)


def _parse_corp_xml(xml_bytes: bytes) -> Dict[str, str]:
    """CORPCODE.xml 본문에서 stock_code → corp_code 매핑을 만든다."""
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise CollectorError(f"DART corpCode XML 파싱 실패: {exc}") from exc

    mapping: Dict[str, str] = {}
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_code = (item.findtext("corp_code") or "").strip()
        if stock_code and corp_code:
            mapping[stock_code] = corp_code
    if not mapping:
        raise CollectorError("DART corpCode XML 에 유효한 종목 매핑이 없습니다.")
    return mapping


def _extract_xml_from_zip(zip_bytes: bytes) -> bytes:
    """DART corpCode.zip 에서 CORPCODE.xml 본문을 추출한다."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".xml"):
                    return zf.read(name)
    except zipfile.BadZipFile as exc:
        raise CollectorError(f"DART corpCode ZIP 형식 오류: {exc}") from exc
    raise CollectorError("DART corpCode ZIP 안에 XML 파일이 없습니다.")


class DartCorpCodeResolver:
    """Open DART corpCode.xml 다운로드·로컬 캐시·조회."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._cache_path = (
            self._settings.project_root / "db" / "cache" / "dart_corp_codes.json"
        )
        self._mapping: Optional[Dict[str, str]] = None

    @property
    def cache_path(self) -> Path:
        return self._cache_path

    def _load_cache_file(self) -> Optional[Dict[str, str]]:
        if not self._cache_path.is_file():
            return None
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            data = payload.get("mapping")
            if isinstance(data, dict) and data:
                return {str(k): str(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            _LOGGER.warning("corp_code 캐시 읽기 실패(%s): %s", self._cache_path, exc)
        return None

    def _save_cache_file(self, mapping: Dict[str, str]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps({"mapping": mapping}, ensure_ascii=False, indent=0),
            encoding="utf-8",
        )

    def _download_mapping(self) -> Dict[str, str]:
        api_key = self._settings.open_dart_api_key
        if not api_key:
            raise CollectorError(
                "OPEN_DART_API_KEY 가 없어 DART corp_code 목록을 받을 수 없습니다."
            )
        try:
            import requests  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise CollectorError(
                "'requests' 패키지가 필요합니다. `pip install -r requirements.txt` 를 실행하세요."
            ) from exc

        url = f"{self._settings.dart_base_url.rstrip('/')}/corpCode.xml"
        timeout = self._settings.http_timeout_seconds
        try:
            resp = requests.get(
                url, params={"crtfc_key": api_key}, timeout=timeout
            )
            resp.raise_for_status()
        except Exception as exc:  # pylint: disable=broad-except
            raise CollectorError(f"DART corpCode 다운로드 실패: {exc}") from exc

        xml_bytes = _extract_xml_from_zip(resp.content)
        mapping = _parse_corp_xml(xml_bytes)
        self._save_cache_file(mapping)
        _LOGGER.info("DART corp_code 캐시 갱신: %d 종목", len(mapping))
        return mapping

    def load_mapping(self, *, refresh: bool = False) -> Dict[str, str]:
        """전체 stock_code → corp_code 매핑을 반환한다."""
        if self._mapping is not None and not refresh:
            return self._mapping

        if not refresh:
            cached = self._load_cache_file()
            if cached:
                self._mapping = cached
                return cached

        try:
            self._mapping = self._download_mapping()
            return self._mapping
        except CollectorError:
            cached = self._load_cache_file()
            if cached:
                _LOGGER.warning("DART 다운로드 실패 — 기존 캐시 사용")
                self._mapping = cached
                return cached
            raise

    def resolve(self, stock_code: str, *, refresh: bool = False) -> str:
        """종목코드에 대한 DART corp_code 를 반환한다."""
        code = (stock_code or "").strip()
        if not code:
            raise CollectorError("stock_code 가 비어 있습니다.")

        fallback = get_default_stock(code)
        if fallback and fallback.corp_code:
            builtin = fallback.corp_code
        else:
            builtin = ""

        try:
            mapping = self.load_mapping(refresh=refresh)
            found = mapping.get(code)
            if found:
                return found
        except CollectorError as exc:
            if builtin:
                _LOGGER.warning(
                    "corp_code API/캐시 실패 — 기본 종목 매핑 사용: %s (%s)",
                    code,
                    exc,
                )
                return builtin
            raise

        if builtin:
            return builtin
        raise CollectorError(
            f"stock_code {code} 에 대한 DART corp_code 를 찾지 못했습니다. "
            "OPEN_DART_API_KEY 설정 후 재시도하거나 --corp-code 를 지정하세요."
        )


def resolve_corp_code(
    stock_code: str,
    *,
    settings: Optional[Settings] = None,
    refresh: bool = False,
) -> str:
    """모듈 수준 corp_code 조회 헬퍼."""
    return DartCorpCodeResolver(settings=settings).resolve(stock_code, refresh=refresh)
