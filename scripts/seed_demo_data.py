# -*- coding: utf-8 -*-
"""삼성전자·SK하이닉스 데모 데이터 일괄 수집·분석 (UTF-8)."""
from __future__ import annotations

import sys
from datetime import datetime

from semi_senti.admin.monitoring import SystemMonitor
from semi_senti.collector import DartFinancialCollector, NaverNewsCollector, PriceCollector
from semi_senti.db import DBControl
from semi_senti.engine import CycleAnalyzer, DivergenceDetector, SentimentEngine, SignalLogic

STOCKS = (
    {
        "stock_code": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "corp_code": "00126380",
        "news_query": "삼성전자 HBM 반도체",
    },
    {
        "stock_code": "000660",
        "name": "SK하이닉스",
        "market": "KOSPI",
        "corp_code": "00164779",
        "news_query": "SK하이닉스 HBM 반도체",
    },
)


def _upsert_stocks(db: DBControl) -> None:
    for s in STOCKS:
        db.upsert(
            "stocks",
            {
                "stock_code": s["stock_code"],
                "name": s["name"],
                "market": s["market"],
                "is_active": 1,
            },
            conflict_columns=["stock_code"],
        )


def _collect_prices() -> None:
    with PriceCollector() as pc:
        for s in STOCKS:
            n = pc.collect_and_store(
                stock_code=s["stock_code"],
                market=s["market"],
                stock_name=s["name"],
                force=True,
            )
            print(f"[price] {s['stock_code']} {s['name']}: {n} rows")


def _collect_news() -> None:
    with NaverNewsCollector() as nc:
        for s in STOCKS:
            n = nc.collect_and_store(
                stock_code=s["stock_code"],
                query=s["news_query"],
                stock_name=s["name"],
                market=s["market"],
                force=True,
            )
            print(f"[news] {s['stock_code']}: {n} new rows")


def _collect_dart() -> None:
    year = str(datetime.now().year - 1)
    with DartFinancialCollector() as dc:
        for s in STOCKS:
            rec = dc.collect_and_store(
                stock_code=s["stock_code"],
                corp_code=s["corp_code"],
                bsns_year=year,
                stock_name=s["name"],
            )
            print(f"[dart] {s['stock_code']}: {rec}")


def _analyze() -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    for s in STOCKS:
        code = s["stock_code"]
        with SentimentEngine() as se:
            sent = se.score_news_and_store(stock_code=code, score_date=today)
            print(f"[sentiment] {code}: score={sent.score:.1f} news={sent.news_count}")
        with SignalLogic() as sl:
            sig = sl.detect_and_store(stock_code=code)
            print(f"[signal] {code}: {sig.signal_type}")
        with DivergenceDetector() as dd:
            div = dd.detect(code)
            print(f"[divergence] {code}: detected={div.detected}")
        with CycleAnalyzer() as ca:
            cyc = ca.analyze_and_store(stock_code=code)
            print(f"[cycle] {code}: phase={cyc.phase} score={cyc.cycle_score:.2f}")


def main() -> int:
    db = DBControl()
    db.connect()
    try:
        _upsert_stocks(db)
        _collect_prices()
        _collect_news()
        _collect_dart()
        _analyze()
        print("\n[admin refresh sanity]")
        mon = SystemMonitor(db=db)
        for s in STOCKS:
            st = mon.stock_status(s["stock_code"])
            print(
                f"  {s['stock_code']}: price={st.last_price_at} news={st.news_count} "
                f"signal={st.signal_count} sentiment={st.last_sentiment_date}"
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
