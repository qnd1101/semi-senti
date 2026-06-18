# -*- coding: utf-8 -*-
"""반도체 15종목 전체 데이터 수집 — 주가 + 재무 + 뉴스 + 감성 + 시그널.

현재 운영 환경과 동일한 수준으로 데이터를 채운다.
실행: python scripts/seed_all_data.py  (또는 collect_all_data.bat)
필요: .env 에 DATABASE_URL + (재무) OPEN_DART_API_KEY + (뉴스) NAVER_CLIENT_ID/SECRET
주가는 pykrx 기반이라 키 없이도 수집된다. KoNLPy(JDK/JAVA_HOME) 미설정 시 감성은 정규식 폴백.
"""
from __future__ import annotations

from semi_senti.db import DBControl
from semi_senti.data.sector_universe import SEMICONDUCTOR_UNIVERSE
from semi_senti.pipeline import get_live_pipeline
from semi_senti.collector.news import NaverNewsCollector
from semi_senti.engine.sentiment import SentimentEngine
from semi_senti.engine import SignalLogic

# 시장 구분 (KOSPI 3종목, 나머지 KOSDAQ)
KOSPI = {"005930", "000660", "000990"}


def main() -> None:
    db = DBControl()
    universe = list(SEMICONDUCTOR_UNIVERSE)
    print("대상 %d종목 - 주가 + 재무 + 뉴스(2년치) + 감성 + 시그널\n" % len(universe), flush=True)

    # 1) 종목 등록
    print("===== 1) 종목 등록 =====", flush=True)
    for code, name in universe:
        market = "KOSPI" if code in KOSPI else "KOSDAQ"
        db.upsert("stocks",
                  {"stock_code": code, "name": name, "market": market, "is_active": 1},
                  conflict_columns=["stock_code"])
    print("  %d종목 등록 완료" % len(universe), flush=True)

    # 2) 주가(전체이력) + 재무(DART)
    print("\n===== 2) 주가 + 재무 (sync, force) =====", flush=True)
    pipe = get_live_pipeline()
    for code, name in universe:
        try:
            r = pipe.sync_stock(code, force=True)
            steps = r.get("steps", {})
            pr = steps.get("price", {}); da = steps.get("dart", {})
            print("  [%s] %s: price_ok=%s dart_ok=%s" % (code, name, pr.get("ok"), da.get("ok")), flush=True)
        except Exception as e:
            print("  [%s] %s: ERROR %s" % (code, name, e), flush=True)

    # 3) 뉴스 (날짜순, 종목당 최대 1000건)
    print("\n===== 3) 뉴스 (날짜순, 종목당 최대 1000건) =====", flush=True)
    with NaverNewsCollector() as nc:
        for code, name in universe:
            total = 0
            for start in range(1, 1001, 100):
                try:
                    total += nc.collect_and_store(stock_code=code, query=name,
                                                  display=100, start=start, sort="date", force=True)
                except Exception as e:
                    print("  [%s] start=%d 중단: %s" % (code, start, e), flush=True)
                    break
            print("  [%s] %s: +%d건 신규" % (code, name, total), flush=True)

    # 4) 감성 분석 (미분석분)
    print("\n===== 4) 뉴스 감성 분석 =====", flush=True)
    eng = SentimentEngine(db=db)
    rows = db.fetch_all("SELECT id, title, summary FROM news WHERE sentiment_score IS NULL ORDER BY id")
    print("  미분석 %d건" % len(rows), flush=True)
    done = 0
    for r in rows:
        text = ("%s %s" % (r.get("title") or "", r.get("summary") or "")).strip()
        try:
            res = eng.analyze_text(text)
            db.update("news",
                      {"sentiment_score": res.score, "sentiment_raw_score": res.raw_score},
                      where="id = %s", where_params=(r["id"],))
            done += 1
        except Exception:
            pass
        if done % 500 == 0 and done:
            print("    %d/%d" % (done, len(rows)), flush=True)
    print("  감성 분석 완료 %d건" % done, flush=True)

    # 5) 다중관점 시그널 산출 (signals 적재 -> 대시보드 "판단 준비중" 해소)
    print("\n===== 5) 다중관점 시그널 산출 =====", flush=True)
    sl = SignalLogic(db=db)
    for code, name in universe:
        try:
            sl.detect_and_store(code)
            print("  [%s] %s: 시그널 산출 완료" % (code, name), flush=True)
        except Exception as e:
            print("  [%s] %s: ERROR %s" % (code, name, e), flush=True)

    # 6) 최종 현황
    print("\n===== 최종 현황 =====", flush=True)
    for code, name in universe:
        f = db.fetch_one("SELECT count(*) c, max(record_date) m FROM financials WHERE stock_code=%s AND close_price IS NOT NULL", (code,))
        n = db.fetch_one("SELECT count(*) c FROM news WHERE stock_code=%s", (code,))
        sg = db.fetch_one("SELECT count(*) c FROM signals WHERE stock_code=%s", (code,))
        print("  %s %s: 주가 %s행 ~%s, 뉴스 %s건, 시그널 %s건" % (code, name, f["c"], f["m"], n["c"], sg["c"]), flush=True)
    print("\n[완료] 전체 수집 완료", flush=True)


if __name__ == "__main__":
    main()
