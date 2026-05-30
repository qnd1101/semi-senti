"use client";

import { CyclePanel } from "@/components/dashboard/CyclePanel";
import { FinancialSummary } from "@/components/dashboard/FinancialSummary";
import { KeywordTrend } from "@/components/dashboard/KeywordTrend";
import { SentimentGauge } from "@/components/dashboard/SentimentGauge";
import { SignalCard } from "@/components/dashboard/SignalCard";
import { SignalChart, INTERVAL_OPTIONS } from "@/components/dashboard/SignalChart";
import { fetchCandles, fetchSnapshot, fetchStocks } from "@/lib/api";
import type { CandleData, DashboardSnapshot } from "@/lib/types";
import { useCallback, useEffect, useRef, useState } from "react";

const AUTO_REFRESH_SEC = parseInt(
  process.env.NEXT_PUBLIC_AUTO_REFRESH_SECONDS || "60",
  10
);

export default function Home() {
  const [stocks, setStocks] = useState<{ stock_code: string; name: string }[]>([]);
  const [selectedCode, setSelectedCode] = useState<string>("");
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [interval, setInterval] = useState("1d");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof globalThis.setTimeout> | null>(null);

  // 종목 목록 로드
  useEffect(() => {
    fetchStocks()
      .then((list) => {
        const active = list.filter((s) => s.is_active === 1);
        setStocks(active);
        if (active.length) setSelectedCode(active[0].stock_code);
      })
      .catch(() => {
        // 백엔드 연결 실패 시 기본 목록
        setStocks([
          { stock_code: "005930", name: "삼성전자" },
          { stock_code: "000660", name: "SK하이닉스" },
        ]);
        setSelectedCode("005930");
      });
  }, []);

  const loadData = useCallback(
    async (code: string, iv: string) => {
      if (!code) return;
      setLoading(true);
      setError(null);
      try {
        const [snap, chart] = await Promise.all([
          fetchSnapshot(code),
          fetchCandles(code, iv),
        ]);
        setSnapshot(snap);
        setCandles(chart.candles);
      } catch (e) {
        setError(e instanceof Error ? e.message : "데이터 로드 실패");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // 종목/봉주기 변경 시 로드
  useEffect(() => {
    if (selectedCode) loadData(selectedCode, interval);
  }, [selectedCode, interval, loadData]);

  // 자동 갱신
  useEffect(() => {
    if (!selectedCode) return;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = globalThis.setInterval(() => loadData(selectedCode, interval), AUTO_REFRESH_SEC * 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [selectedCode, interval, loadData]);

  const stock = snapshot?.stock;
  const sentimentEmpty = {
    score: null,
    raw_score: null,
    news_count: null,
    score_date: "",
    top_keywords: null,
  };

  return (
    <main className="min-h-screen bg-[#09090b] text-zinc-100 flex flex-col">
      {/* Topbar */}
      <header className="h-12 border-b border-zinc-800/60 flex items-center px-4 gap-4 flex-shrink-0">
        <span className="font-semibold text-sm">Semi Senti</span>
        <span className="text-xs text-zinc-500">반도체 감성 분석 대시보드</span>
        <div className="ml-auto flex items-center gap-2">
          {/* 종목 선택 */}
          <select
            className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none"
            value={selectedCode}
            onChange={(e) => setSelectedCode(e.target.value)}
          >
            {stocks.map((s) => (
              <option key={s.stock_code} value={s.stock_code}>
                {s.name} ({s.stock_code})
              </option>
            ))}
          </select>
          {/* 봉주기 */}
          <div className="flex gap-1">
            {INTERVAL_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                className={`px-2 py-1 text-xs rounded border transition
                  ${interval === opt.id
                    ? "bg-zinc-700 border-zinc-600 text-zinc-100"
                    : "border-zinc-800 text-zinc-500 hover:text-zinc-300"}`}
                onClick={() => setInterval(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {loading && <span className="text-xs text-zinc-500 animate-pulse">갱신 중…</span>}
        </div>
      </header>

      {error && (
        <div className="mx-4 mt-2 px-3 py-2 text-xs bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded">
          ⚠ {error} — 백엔드(localhost:8001)가 실행 중인지 확인하세요.
        </div>
      )}

      {/* 메인 그리드 — 1화면 집중 원칙 */}
      <div className="flex-1 grid grid-cols-[1fr_280px] gap-3 p-3 overflow-hidden" style={{ minHeight: 0 }}>
        {/* 좌: 차트 + 3관점 시그널 */}
        <div className="flex flex-col gap-3 overflow-hidden" style={{ minHeight: 0 }}>
          {/* 차트 */}
          <div className="glass-card flex-1 p-3 overflow-hidden" style={{ minHeight: 0 }}>
            <div className="h-full">
              {candles.length > 0 ? (
                <SignalChart
                  candles={candles}
                  signals={snapshot?.signals}
                  bandLow={snapshot?.price.band_low}
                  bandHigh={snapshot?.price.band_high}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-600 text-sm">
                  {loading ? "차트 로딩 중…" : "데이터 없음"}
                </div>
              )}
            </div>
          </div>

          {/* 3관점 시그널 카드 */}
          <div className="grid grid-cols-3 gap-3 flex-shrink-0">
            {(["SHORT", "MID", "LONG"] as const).map((persp) => (
              <SignalCard
                key={persp}
                perspective={persp}
                signal={snapshot?.signals[persp.toLowerCase() as "short" | "mid" | "long"] ?? null}
                reasoning={snapshot?.reasonings[persp.toLowerCase() as "short" | "mid" | "long"] ?? null}
              />
            ))}
          </div>
        </div>

        {/* 우: 감성 게이지 + 키워드 + 재무 + 사이클 */}
        <div className="flex flex-col gap-3 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
          {/* 종목명 */}
          {stock && (
            <div className="px-1">
              <h1 className="text-base font-semibold">{stock.name}</h1>
              <p className="text-xs text-zinc-500">{stock.stock_code} · {stock.market}</p>
            </div>
          )}

          {/* 감성 게이지 */}
          <div className="glass-card p-4">
            <p className="text-xs text-zinc-400 mb-2">감성 지수</p>
            <SentimentGauge sentiment={snapshot?.sentiment || sentimentEmpty} />
          </div>

          {/* 핵심 키워드 */}
          <div className="glass-card p-4">
            <p className="text-xs text-zinc-400 mb-2">핵심 키워드</p>
            <KeywordTrend keywords={snapshot?.sentiment.top_keywords} />
          </div>

          {/* 재무 요약 */}
          <div className="glass-card p-4">
            <p className="text-xs text-zinc-400 mb-2">재무 & 밴드</p>
            {snapshot ? (
              <FinancialSummary price={snapshot.price} financials={snapshot.financials} />
            ) : (
              <p className="text-xs text-zinc-500">데이터 없음</p>
            )}
          </div>

          {/* 업황 사이클 */}
          <div className="glass-card p-4">
            <p className="text-xs text-zinc-400 mb-2">업황 사이클</p>
            <CyclePanel cycle={snapshot?.cycle ?? null} />
          </div>

          {/* 차트 요약 */}
          {snapshot?.chart_summary && (
            <div className="px-1 text-[10px] text-zinc-600">
              일봉 {snapshot.chart_summary.first_date} ~ {snapshot.chart_summary.last_date} ({snapshot.chart_summary.bar_count}거래일)
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
