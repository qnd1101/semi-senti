"""실시간 데이터 파이프라인 — 초기 DART 재무 수집 + 주가 주기 폴링.

FastAPI 기동 시 백그라운드 스레드에서:
1. DB 초기화 및 기본 종목(삼성전자·SK하이닉스) 등록
2. Open DART API로 재무 요약(매출·영업이익·PER·PBR·EPS) 적재
3. yfinance로 전체·최신 주가 수집 후 ``PRICE_POLL_INTERVAL_SECONDS`` 간격으로 반복 갱신
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import List, Optional

from ..collector import CollectorError, DartFinancialCollector, PriceCollector
from ..collector.dart_corp import resolve_corp_code
from ..config import Settings, get_settings
from ..data.default_stocks import ensure_default_stocks_registered, get_default_stock, iter_default_stocks
from ..db import DBControl, init_database

_LOGGER = logging.getLogger(__name__)

_pipeline: Optional["LiveDataPipeline"] = None
_pipeline_lock = threading.Lock()


def _active_stocks(db: DBControl) -> List[dict]:
    return db.fetch_all(
        "SELECT stock_code, name, market FROM stocks WHERE is_active = 1 ORDER BY stock_code"
    )


def _has_price_data(db: DBControl, stock_code: str) -> bool:
    row = db.fetch_one(
        "SELECT 1 FROM financials "
        "WHERE stock_code = ? AND close_price IS NOT NULL "
        "LIMIT 1",
        (stock_code,),
    )
    return row is not None


def _stock_row(db: DBControl, stock_code: str) -> Optional[dict]:
    return db.fetch_one(
        "SELECT stock_code, name, market FROM stocks WHERE stock_code = ?",
        (stock_code,),
    )


def _has_financial_summary(db: DBControl, stock_code: str) -> bool:
    row = db.fetch_one(
        "SELECT 1 FROM financials "
        "WHERE stock_code = ? AND revenue IS NOT NULL "
        "LIMIT 1",
        (stock_code,),
    )
    return row is not None


class LiveDataPipeline:
    """초기 동기화 + 주기적 주가 폴링."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def ensure_defaults(self) -> None:
        """DB 초기화 및 기본 종목(삼성전자·SK하이닉스) 등록."""
        init_database(db_path=self._settings.sqlite_path, force=False)
        with DBControl(db_path=self._settings.sqlite_path) as db:
            ensure_default_stocks_registered(db)

    def sync_stock(self, stock_code: str, *, force: bool = False) -> dict:
        """단일 종목 주가·DART 재무를 DB에 없으면 수집한다."""
        code = (stock_code or "").strip()
        if not code:
            raise ValueError("stock_code 는 필수입니다.")

        result: dict = {"stock_code": code, "steps": {}, "ok": True}
        init_database(db_path=self._settings.sqlite_path, force=False)

        with DBControl(db_path=self._settings.sqlite_path) as db:
            ensure_default_stocks_registered(db)
            row = _stock_row(db, code)
            if row is None:
                meta = get_default_stock(code)
                if meta is None:
                    raise ValueError(f"등록되지 않은 종목: {code}")
                db.upsert(
                    "stocks",
                    {
                        "stock_code": meta.stock_code,
                        "name": meta.name,
                        "market": meta.market,
                        "is_active": 1,
                    },
                    conflict_columns=["stock_code"],
                    update_columns=["name", "market", "is_active"],
                )
                row = _stock_row(db, code)

            market = row.get("market") or "KOSPI"
            name = row.get("name")
            needs_price = force or not _has_price_data(db, code)
            needs_dart = force or not _has_financial_summary(db, code)

            if needs_price:
                try:
                    with PriceCollector(db=db, settings=self._settings) as pc:
                        full_rows = pc.collect_full_history_and_store(
                            stock_code=code,
                            market=market,
                            stock_name=name,
                            force=True,
                        )
                        rows = pc.collect_and_store(
                            stock_code=code,
                            market=market,
                            stock_name=name,
                            force=True,
                        )
                    result["steps"]["price"] = {
                        "ok": True,
                        "history_rows": int(full_rows),
                        "rows": int(rows),
                    }
                except CollectorError as exc:
                    result["steps"]["price"] = {"ok": False, "error": str(exc)}
                    result["ok"] = False
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.exception("주가 수집 예외 (%s): %s", code, exc)
                    result["steps"]["price"] = {"ok": False, "error": str(exc)}
                    result["ok"] = False
            else:
                result["steps"]["price"] = {"ok": True, "skipped": True}

            if needs_dart:
                if not self._settings.open_dart_api_key:
                    result["steps"]["dart"] = {
                        "ok": False,
                        "skipped": True,
                        "reason": "OPEN_DART_API_KEY 미설정",
                    }
                else:
                    year = str(datetime.now().year - 1)
                    try:
                        meta = get_default_stock(code)
                        corp_code = (
                            meta.corp_code
                            if meta and meta.corp_code
                            else resolve_corp_code(code, settings=self._settings)
                        )
                        with DartFinancialCollector(db=db, settings=self._settings) as dc:
                            record = dc.collect_and_store(
                                stock_code=code,
                                corp_code=corp_code,
                                bsns_year=year,
                                stock_name=name or (meta.name if meta else None),
                            )
                        result["steps"]["dart"] = {"ok": True, "record": record}
                    except CollectorError as exc:
                        result["steps"]["dart"] = {"ok": False, "error": str(exc)}
                        result["ok"] = False
                    except Exception as exc:  # pylint: disable=broad-except
                        _LOGGER.exception("DART 수집 예외 (%s): %s", code, exc)
                        result["steps"]["dart"] = {"ok": False, "error": str(exc)}
                        result["ok"] = False
            else:
                result["steps"]["dart"] = {"ok": True, "skipped": True}

        return result

    def run_startup_sync(self) -> None:
        """DB 준비, 기본 종목 등록, DART 재무·초기 주가 수집."""
        init_database(db_path=self._settings.sqlite_path, force=False)
        with DBControl(db_path=self._settings.sqlite_path) as db:
            ensure_default_stocks_registered(db)
            self._sync_dart_for_defaults(db)
            self._sync_prices(db, force=True)

    def _sync_dart_for_defaults(self, db: DBControl) -> None:
        if not self._settings.open_dart_api_key:
            _LOGGER.warning(
                "OPEN_DART_API_KEY 미설정 — DART 재무 수집을 건너뜁니다. "
                "재무 요약 패널은 API 키 설정 후 서버 재시작 시 채워집니다."
            )
            return

        year = str(datetime.now().year - 1)
        with DartFinancialCollector(db=db, settings=self._settings) as dc:
            for stock in iter_default_stocks():
                if _has_financial_summary(db, stock.stock_code) and dc.is_cache_fresh(
                    stock.stock_code
                ):
                    _LOGGER.info("DART 캐시 신선 → 건너뜀: %s", stock.stock_code)
                    continue
                try:
                    corp_code = stock.corp_code or resolve_corp_code(
                        stock.stock_code, settings=self._settings
                    )
                    dc.collect_and_store(
                        stock_code=stock.stock_code,
                        corp_code=corp_code,
                        bsns_year=year,
                        stock_name=stock.name,
                    )
                except CollectorError as exc:
                    _LOGGER.error("DART 수집 실패 (%s): %s", stock.stock_code, exc)
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.exception("DART 수집 예외 (%s): %s", stock.stock_code, exc)

    def _sync_prices(self, db: DBControl, *, force: bool) -> None:
        stocks = _active_stocks(db)
        if not stocks:
            _LOGGER.warning("활성 종목 없음 — 주가 수집 건너뜀")
            return

        with PriceCollector(db=db, settings=self._settings) as pc:
            for row in stocks:
                code = row["stock_code"]
                market = row.get("market") or "KOSPI"
                name = row.get("name")
                try:
                    full_rows = pc.collect_full_history_and_store(
                        stock_code=code,
                        market=market,
                        stock_name=name,
                        force=force,
                    )
                    _LOGGER.info("전체 주가 동기화: %s rows=%d", code, full_rows)
                    rows = pc.collect_and_store(
                        stock_code=code,
                        market=market,
                        stock_name=name,
                        force=True,
                    )
                    _LOGGER.debug("주가 갱신: %s rows=%d", code, rows)
                except CollectorError as exc:
                    _LOGGER.error("주가 수집 실패 (%s): %s", code, exc)
                except Exception as exc:  # pylint: disable=broad-except
                    _LOGGER.exception("주가 수집 예외 (%s): %s", code, exc)

    def poll_prices_once(self) -> None:
        """활성 종목 주가 1회 갱신 (TTL 무시)."""
        with DBControl(db_path=self._settings.sqlite_path) as db:
            self._sync_prices(db, force=True)

    def _worker(self) -> None:
        try:
            self.run_startup_sync()
            _LOGGER.info("초기 데이터 동기화 완료 — 주가 폴링 시작")
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.exception("초기 데이터 동기화 실패: %s", exc)

        interval = max(15, self._settings.price_poll_interval_seconds)
        while not self._stop.is_set():
            if self._stop.wait(interval):
                break
            try:
                self.poll_prices_once()
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("주가 폴링 실패: %s", exc)

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._worker,
            name="semi-senti-live-data",
            daemon=True,
        )
        self._thread.start()
        _LOGGER.info(
            "LiveDataPipeline 시작 (주가 폴링 간격=%ds)",
            self._settings.price_poll_interval_seconds,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=15)
            self._thread = None
        _LOGGER.info("LiveDataPipeline 종료")


def get_live_pipeline(settings: Optional[Settings] = None) -> LiveDataPipeline:
    global _pipeline  # noqa: PLW0603
    with _pipeline_lock:
        if _pipeline is None:
            _pipeline = LiveDataPipeline(settings=settings)
        return _pipeline


def start_live_pipeline(settings: Optional[Settings] = None) -> LiveDataPipeline:
    pipeline = get_live_pipeline(settings)
    if not pipeline.running:
        pipeline.start()
    return pipeline


def stop_live_pipeline() -> None:
    global _pipeline  # noqa: PLW0603
    with _pipeline_lock:
        if _pipeline is not None:
            _pipeline.stop()
            _pipeline = None
