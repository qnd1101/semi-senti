# -*- coding: utf-8 -*-
"""반도체 15종목 전체 데이터 수집 — 주가(전체이력) + 재무(DART) + 뉴스(2년치) + 감성분석.

현재 운영 환경과 동일한 수준으로 데이터를 채운다.
실행: python scripts/seed_all_data.py  (또는 collect_all_data.bat)
필요: .env 에 DATABASE_URL + (재무) OPEN_DART_API_KEY + (뉴스) NAVER_CLIENT_ID/SECRET
주가는 pykrx 기반이라 키 없이도 수집된다.
"""
from __future__ import annotations

from semi_senti.db import DBControl
from semi_senti.data.sector_universe import SEMICONDUCTOR_UNIVERSE
from semi_senti.pipeline import get_live_pipeline
from semi_senti.collector.news import NaverNewsCollector
from semi_senti.engine.sentiment import SentimentEngine

# 시장 구분 (KOSPI 3종목, 나머지 KOSDAQ)
KOSPI = {"005930", "000660", "000990"}


def main() -> None:
    db = DBControl()
    universe = list(SEMICONDUCTOR_UNIVERSE)
    print(f"대상 {len(universe)}종목 — 주가 + 재무 + 뉴스(2년치) + 감성분석\n", flush=True)

    # 1) 종목 등록 (stocks)
    print("===== 1) 종목 등록 =====", flush=True)
    for code, name in universe:
        market = "KOSPI" if code in KOSPI else "KOSDAQ"
        db.upsert("stocks",
                  {"stock_code": code, "name": name, "market": market, "is_active": 1},
                  conflict_columns=["stock_code"])
    print(f"  {len(universe)}종목 등록 완료", flush=True)

    # 2) 주가(전체이력) + 재무(DART) — pipeline.sync_stock
    print("\n===== 2) 주가 + 재무 (sync, force) =====", flush=True)
    pipe = get_live_pipeline()
    for code, name in universe:
        try:
            r = pipe.sync_stock(code, force=True)
            steps = r.get("steps", {})
            pr = steps.get("price", {}); da = steps.get("dart", {})
            print(f"  [{code}] {name}: price_ok={pr.get('ok')} dart_ok={da.get('ok')}", flush=True)
        except Exception as e:
            print(f"  [{code}] {name}: ERROR {e}", flush=True)

    # 3) 뉴스 (2년치, 종목당 최대 1000건 — 날짜순 페이징)
    print("\n===== 3) 뉴스 (날짜순, 종목당 최대 1000건) =====", flush=True)
    with NaverNewsCollector() as nc:
        for code, name in universe:
            total = 0
            for start in range(1, 1001, 100):
                try:
                    total += nc.collect_and_store(stock_code=code, query=name,
                                                  display=100, start=start, sort="date", force=True)
                except Exception as e:
                    print(f"  [{code}] start={start} 중단: {e}", flush=True)
                    break
            print(f"  [{code}] {name}: +{total}건 신규", flush=True)

    # 4) 감성 분석 (미분석 전체)
    print("\n===== 4) 뉴스 감성 분석 (미분석분) =====", flush=True)
    eng = SentimentEngine(db=db)
    rows = db.fetch_all("SELECT id, title, summary FROM news WHERE sentiment_score IS NULL ORDER BY id")
    print(f"  미분석 {len(rows)}건 분석 시작", flush=True)
    done = 0
    for r in rows:
        text = f"{r.get('title') or ''} {r.get('summary') or ''}".strip()
        try:
            res = eng.analyze_text(text)
            db.update("news",
                      {"sentiment_score": res.score, "sentiment_raw_score": res.raw_score},
                      where="id = %s", where_params=(r["id"],))
            done += 1
        except Exception:
            pass
        if done % 500 == 0 and done:
            print(f"    {done}/{len(rows)}", flush=True)
    print(f"  감성 분석 완료 {done}건", flush=True)

    # 5) 최종 현황
    print("\n===== 최종 현황 =====", flush=True)
    for code, name in universe:
        f = db.fetch_one("SELECT count(*) c, max(record_date) m FROM financials WHERE stock_code=%s AND close_price IS NOT NULL", (code,))
        n = db.fetch_one("SELECT count(*) c FROM news WHERE stock_code=%s", (code,))
        print(f"  {code} {name}: 주가 {f['c']}행 ~{f['m']}, 뉴스 {n['c']}건", flush=True)
    print("\n✅ 전체 수집 완료", flush=True)


if __name__ == "__main__":
    main()
