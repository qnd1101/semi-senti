"""원클릭 부트스트랩: DB 시딩·기본 종목 등록·수집·분석 일괄 실행."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Sequence

from .collector import (
    CollectorError,
    DartFinancialCollector,
    NaverNewsCollector,
    PriceCollector,
)
from .collector.dart_corp import resolve_corp_code
from .config.settings import Settings, get_settings
from .data.default_stocks import DefaultStock, iter_default_stocks
from .db import DBControl, init_database
from .engine import CycleAnalyzer, DivergenceDetector, SentimentEngine, SignalLogic

_LOGGER = logging.getLogger(__name__)


@dataclass
class StockBootstrapResult:
    stock_code: str
    name: str
    steps: dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class BootstrapReport:
    results: List[StockBootstrapResult] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results) and not self.skipped


def _upsert_stock(db: DBControl, stock: DefaultStock) -> None:
    db.upsert(
        "stocks",
        {
            "stock_code": stock.stock_code,
            "name": stock.name,
            "market": stock.market,
            "is_active": 1,
        },
        conflict_columns=["stock_code"],
    )


def _bootstrap_one_stock(
    stock: DefaultStock,
    *,
    settings: Settings,
    skip_collect: bool,
    skip_analyze: bool,
    force: bool,
) -> StockBootstrapResult:
    result = StockBootstrapResult(stock_code=stock.stock_code, name=stock.name)
    code = stock.stock_code

    if skip_collect and skip_analyze:
        result.steps["register"] = {"ok": True}
        return result

    if not skip_collect:
        try:
            with PriceCollector(settings=settings) as pc:
                rows = pc.collect_and_store(
                    stock_code=code,
                    market=stock.market,
                    stock_name=stock.name,
                    force=force,
                )
            result.steps["price"] = {"ok": True, "rows": int(rows)}
        except Exception as exc:  # pylint: disable=broad-except
            result.steps["price"] = {"ok": False, "error": str(exc)}
            result.errors.append(f"price: {exc}")

        if settings.naver_client_id and settings.naver_client_secret:
            try:
                with NaverNewsCollector(settings=settings) as nc:
                    rows = nc.collect_and_store(
                        stock_code=code,
                        query=stock.news_query,
                        stock_name=stock.name,
                        market=stock.market,
                        force=force,
                    )
                result.steps["news"] = {"ok": True, "rows": int(rows)}
            except Exception as exc:  # pylint: disable=broad-except
                result.steps["news"] = {"ok": False, "error": str(exc)}
                result.errors.append(f"news: {exc}")
        else:
            result.steps["news"] = {
                "ok": False,
                "skipped": True,
                "reason": "NAVER_CLIENT_ID/SECRET 미설정",
            }

        if settings.open_dart_api_key:
            try:
                corp_code = resolve_corp_code(code, settings=settings)
                year = str(datetime.now().year - 1)
                with DartFinancialCollector(settings=settings) as dc:
                    record = dc.collect_and_store(
                        stock_code=code,
                        corp_code=corp_code,
                        bsns_year=year,
                        stock_name=stock.name,
                    )
                result.steps["dart"] = {"ok": True, "corp_code": corp_code, "record": record}
            except CollectorError as exc:
                result.steps["dart"] = {"ok": False, "error": str(exc)}
                result.errors.append(f"dart: {exc}")
            except Exception as exc:  # pylint: disable=broad-except
                result.steps["dart"] = {"ok": False, "error": str(exc)}
                result.errors.append(f"dart: {exc}")
        else:
            result.steps["dart"] = {
                "ok": False,
                "skipped": True,
                "reason": "OPEN_DART_API_KEY 미설정",
            }

    if not skip_analyze:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            with SentimentEngine(settings=settings) as se:
                sent = se.score_news_and_store(stock_code=code, score_date=today)
            result.steps["sentiment"] = {
                "ok": True,
                "score": float(sent.score),
                "news_count": int(sent.news_count),
            }
        except Exception as exc:  # pylint: disable=broad-except
            result.steps["sentiment"] = {"ok": False, "error": str(exc)}
            result.errors.append(f"sentiment: {exc}")

        try:
            with SignalLogic(settings=settings) as sl:
                decision = sl.detect_and_store(stock_code=code)
            result.steps["signal"] = {"ok": True, "type": decision.signal_type}
        except Exception as exc:  # pylint: disable=broad-except
            result.steps["signal"] = {"ok": False, "error": str(exc)}
            result.errors.append(f"signal: {exc}")

        try:
            with DivergenceDetector(settings=settings) as dd:
                div = dd.detect(stock_code=code)
            result.steps["divergence"] = {"ok": True, "detected": div.detected}
        except Exception as exc:  # pylint: disable=broad-except
            result.steps["divergence"] = {"ok": False, "error": str(exc)}
            result.errors.append(f"divergence: {exc}")

        try:
            with CycleAnalyzer(settings=settings) as ca:
                cycle = ca.analyze_and_store(stock_code=code)
            result.steps["cycle"] = {
                "ok": True,
                "phase": cycle.phase,
                "score": float(cycle.cycle_score),
            }
        except Exception as exc:  # pylint: disable=broad-except
            result.steps["cycle"] = {"ok": False, "error": str(exc)}
            result.errors.append(f"cycle: {exc}")

    return result


def run_bootstrap(
    *,
    settings: Optional[Settings] = None,
    stock_codes: Optional[Sequence[str]] = None,
    skip_db_seed: bool = False,
    skip_collect: bool = False,
    skip_analyze: bool = False,
    force: bool = True,
) -> BootstrapReport:
    """기본 종목 등록 후 수집·분석을 일괄 수행한다."""
    cfg = settings or get_settings()
    report = BootstrapReport()
    stocks = iter_default_stocks(stock_codes)

    if not stocks:
        report.skipped.append("요청한 종목코드가 기본 목록에 없습니다.")
        return report

    if not skip_db_seed:
        root = cfg.project_root
        seed_script = root / "db_seed.py"
        if seed_script.is_file():
            subprocess.run(
                [sys.executable, str(seed_script)],
                cwd=str(root),
                check=False,
            )
        else:
            init_database(db_path=cfg.sqlite_path, force=False)
    else:
        init_database(db_path=cfg.sqlite_path, force=False)

    db = DBControl(db_path=cfg.sqlite_path)
    db.connect()
    try:
        for stock in stocks:
            _upsert_stock(db, stock)
            report.results.append(
                _bootstrap_one_stock(
                    stock,
                    settings=cfg,
                    skip_collect=skip_collect,
                    skip_analyze=skip_analyze,
                    force=force,
                )
            )
    finally:
        db.close()

    return report


def print_bootstrap_report(report: BootstrapReport) -> None:
    """부트스트랩 결과를 콘솔에 출력한다."""
    for item in report.results:
        status = "OK" if item.ok else "PARTIAL"
        print(f"\n[{status}] {item.name} ({item.stock_code})")
        for step, payload in item.steps.items():
            print(f"  - {step}: {payload}")
        if item.errors:
            print(f"  errors: {item.errors}")
    if report.skipped:
        print("\n[WARN] " + "; ".join(report.skipped))
