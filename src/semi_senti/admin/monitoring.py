"""시스템 모니터링 + 수동 갱신 (T-047, F-6.1.3, UC-07).

> "전체 시스템 동작 상태(데이터 수집·분석 엔진)를 모니터링할 수 있는 화면을 제공한다."
> "특정 종목의 데이터를 즉시 갱신하여 최신 분석 결과를 확보한다."

본 모듈은 1인 운영자 관점의 *상태 요약 + 단발성 갱신 트리거* 를 제공한다.
무거운 스케줄러/대시보드 위젯은 ``dashboard/admin_panel.py`` (Streamlit) 에서
호출한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl, DBControlError

_LOGGER = logging.getLogger(__name__)


@dataclass
class StockStatusSummary:
    """단일 종목의 상태 요약."""

    stock_code: str
    name: str
    market: Optional[str]
    is_active: int
    last_price_at: Optional[str] = None
    last_news_at: Optional[str] = None
    last_signal_at: Optional[str] = None
    last_sentiment_date: Optional[str] = None
    signal_count: int = 0
    news_count: int = 0


@dataclass
class SystemStatusReport:
    """전체 시스템 상태 보고서."""

    generated_at: str
    db_path: str
    table_counts: Dict[str, int] = field(default_factory=dict)
    failed_notifications: int = 0
    stocks: List[StockStatusSummary] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SystemMonitor:
    """수집·분석 상태 모니터링 + 수동 갱신 트리거.

    - 본 클래스 자체는 *상태 요약* 만 책임진다.
    - 수동 갱신은 ``manual_refresh`` 가 collector / engine / notifier 를
      차례대로 호출하여 결과를 dict 로 반환한다.
    """

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

    def __enter__(self) -> "SystemMonitor":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ status
    def status_report(self) -> SystemStatusReport:
        """모든 종목의 수집/분석 상태를 요약한 보고서를 생성한다."""
        report = SystemStatusReport(
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            db_path=str(self._settings.sqlite_path),
        )

        report.table_counts = self._count_all_tables()
        report.failed_notifications = self._count_failed_notifications()

        try:
            stocks = self.db().fetch_all(
                "SELECT stock_code, name, market, is_active "
                "FROM stocks ORDER BY name ASC"
            )
        except DBControlError as exc:
            report.warnings.append(f"stocks 조회 실패: {exc}")
            return report

        for row in stocks:
            try:
                summary = self._summarize_stock(row)
                report.stocks.append(summary)
            except Exception as exc:  # pylint: disable=broad-except
                report.warnings.append(
                    f"{row.get('stock_code')}: 상태 요약 실패 ({exc})"
                )
        return report

    def _count_all_tables(self) -> Dict[str, int]:
        from ..db.schema import ALL_TABLES

        counts: Dict[str, int] = {}
        for table in ALL_TABLES:
            try:
                row = self.db().fetch_one(f'SELECT COUNT(*) AS cnt FROM "{table}"')
                counts[table] = int((row or {}).get("cnt") or 0)
            except DBControlError:
                counts[table] = -1
        return counts

    def _count_failed_notifications(self) -> int:
        try:
            row = self.db().fetch_one(
                "SELECT COUNT(*) AS cnt FROM notifications WHERE status = 'FAILED'"
            )
            return int((row or {}).get("cnt") or 0)
        except DBControlError:
            return 0

    def _summarize_stock(self, row: Dict[str, Any]) -> StockStatusSummary:
        code = row["stock_code"]
        last_price = self._fetch_one(
            "SELECT MAX(updated_at) AS at FROM financials WHERE stock_code = ?",
            (code,),
        )
        last_news = self._fetch_one(
            "SELECT MAX(collected_at) AS at, COUNT(*) AS cnt FROM news WHERE stock_code = ?",
            (code,),
        )
        last_signal = self._fetch_one(
            "SELECT MAX(signaled_at) AS at, COUNT(*) AS cnt FROM signals WHERE stock_code = ?",
            (code,),
        )
        last_sent = self._fetch_one(
            "SELECT MAX(score_date) AS at FROM sentiment_scores WHERE stock_code = ?",
            (code,),
        )
        return StockStatusSummary(
            stock_code=code,
            name=row.get("name") or code,
            market=row.get("market"),
            is_active=int(row.get("is_active") or 0),
            last_price_at=(last_price or {}).get("at"),
            last_news_at=(last_news or {}).get("at"),
            news_count=int((last_news or {}).get("cnt") or 0),
            last_signal_at=(last_signal or {}).get("at"),
            signal_count=int((last_signal or {}).get("cnt") or 0),
            last_sentiment_date=(last_sent or {}).get("at"),
        )

    def _fetch_one(self, sql: str, params: tuple) -> Optional[Dict[str, Any]]:
        try:
            return self.db().fetch_one(sql, params)
        except DBControlError as exc:
            _LOGGER.warning("monitor query 실패: %s", exc)
            return None

    # ------------------------------------------------------------------ manual refresh (UC-07)
    def manual_refresh(
        self,
        stock_code: str,
        *,
        market: str = "KOSPI",
        news_query: Optional[str] = None,
        run_signal: bool = True,
        run_sentiment: bool = True,
        run_cycle: bool = True,
    ) -> Dict[str, Any]:
        """단일 종목을 즉시 갱신 (UC-07).

        - 수집·분석 단계가 실패해도 후속 단계가 가능한 경우 계속 진행한다.
        - 결과는 단계별 dict 로 모아 반환한다.
        """
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        result: Dict[str, Any] = {
            "stock_code": stock_code,
            "started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "steps": {},
            "errors": [],
        }

        # 1) 가격 수집
        try:
            from ..collector import PriceCollector

            with PriceCollector(db=self.db(), settings=self._settings) as pc:
                count = pc.collect_and_store(
                    stock_code=stock_code,
                    market=market,
                    force=True,
                )
            result["steps"]["price"] = {"ok": True, "rows": int(count)}
        except Exception as exc:  # pylint: disable=broad-except
            result["steps"]["price"] = {"ok": False, "error": str(exc)}
            result["errors"].append(f"price: {exc}")

        # 2) 뉴스 수집 (query 가 명시된 경우만)
        if news_query:
            try:
                from ..collector import NaverNewsCollector

                with NaverNewsCollector(db=self.db(), settings=self._settings) as nc:
                    rows = nc.collect_and_store(
                        stock_code=stock_code, query=news_query, force=True
                    )
                result["steps"]["news"] = {"ok": True, "rows": int(rows)}
            except Exception as exc:  # pylint: disable=broad-except
                result["steps"]["news"] = {"ok": False, "error": str(exc)}
                result["errors"].append(f"news: {exc}")

        # 3) 감성 분석 + 적재
        if run_sentiment:
            try:
                from ..engine import SentimentEngine

                today = datetime.utcnow().strftime("%Y-%m-%d")
                with SentimentEngine(db=self.db(), settings=self._settings) as se:
                    sent = se.score_news_and_store(
                        stock_code=stock_code, score_date=today
                    )
                result["steps"]["sentiment"] = {
                    "ok": True,
                    "score": float(sent.score),
                    "news_count": int(sent.news_count),
                    "score_date": today,
                }
            except Exception as exc:  # pylint: disable=broad-except
                result["steps"]["sentiment"] = {"ok": False, "error": str(exc)}
                result["errors"].append(f"sentiment: {exc}")

        # 4) 시그널 산출 + 적재
        if run_signal:
            try:
                from ..engine import SignalLogic

                with SignalLogic(db=self.db(), settings=self._settings) as sl:
                    decision = sl.detect_and_store(stock_code=stock_code)
                result["steps"]["signal"] = {
                    "ok": True,
                    "signal_type": decision.signal_type,
                    "rationale": decision.rationale,
                }
            except Exception as exc:  # pylint: disable=broad-except
                result["steps"]["signal"] = {"ok": False, "error": str(exc)}
                result["errors"].append(f"signal: {exc}")

        # 5) 사이클 분석 (T-045)
        if run_cycle:
            try:
                from ..engine import CycleAnalyzer

                with CycleAnalyzer(db=self.db(), settings=self._settings) as ca:
                    cycle = ca.analyze_and_store(stock_code=stock_code)
                result["steps"]["cycle"] = {
                    "ok": True,
                    "score": float(cycle.cycle_score),
                    "phase": cycle.phase,
                }
            except Exception as exc:  # pylint: disable=broad-except
                result["steps"]["cycle"] = {"ok": False, "error": str(exc)}
                result["errors"].append(f"cycle: {exc}")

        result["finished_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        result["ok"] = not result["errors"]
        return result
