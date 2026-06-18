"use client";

import { useMemo, useState, useCallback } from "react";

import { Sidebar, MobileTabBar } from "@/components/dashboard-c/Sidebar";
import { Screener } from "@/components/dashboard-c/Screener";
import { TickerSelector } from "@/components/dashboard-c/TickerSelector";
import { StockHeader } from "@/components/dashboard-c/StockHeader";
import { SoonToast } from "@/components/dashboard-c/SoonToast";

import { TrafficLightHero } from "@/components/dashboard-c/TrafficLightHero";
import { WhyCards } from "@/components/dashboard-c/WhyCards";
import { GapCompare } from "@/components/dashboard-c/GapCompare";
import { CycleBar } from "@/components/dashboard-c/CycleBar";
import { HorizonRows } from "@/components/dashboard-c/HorizonRows";
import { LineChartWithMarkers } from "@/components/dashboard-c/LineChartWithMarkers";
import { CandleChart } from "@/components/dashboard-c/CandleChart";
import { EvidenceAccordion } from "@/components/dashboard-c/EvidenceAccordion";
import { AiReasonings } from "@/components/dashboard-c/AiReasonings";

import { NewsBanner } from "@/components/dashboard-c/NewsBanner";
import { NewsFilters, type NewsFilter, type NewsDays } from "@/components/dashboard-c/NewsFilters";
import { NewsList, type NewsState } from "@/components/dashboard-c/NewsList";

import { FinanceCards } from "@/components/dashboard-c/FinanceCards";
import { FinanceBand } from "@/components/dashboard-c/FinanceBand";
import { FinanceDisclosure } from "@/components/dashboard-c/FinanceDisclosure";

import { useStocks, useSnapshot, useCandles, useNews } from "@/lib/dashboard-c/hooks";
import { adaptTickers, adaptSnapshot, adaptNews } from "@/lib/dashboard-c/adapt";
import { relativeTime } from "@/lib/dashboard-c/format";
import { C } from "@/lib/dashboard-c/tokens";

// ViewKey 타입 export — Sidebar에서 import 함
export type ViewKey = "screener" | "home" | "chart" | "news" | "finance";

const NEWS_API_READY = process.env.NEXT_PUBLIC_NEWS_API_READY !== "false";

export default function Home() {
  const [view, setView] = useState<ViewKey>("screener");
  const [activeTicker, setActiveTicker] = useState<string>("");
  const [newsFilter, setNewsFilter] = useState<NewsFilter>("all");
  const [newsDays, setNewsDays] = useState<NewsDays>(30);
  const [toast, setToast] = useState<string | null>(null);

  const { data: stockRows } = useStocks();

  const tickers = useMemo(() => (stockRows ? adaptTickers(stockRows) : []), [stockRows]);

  const effectiveTicker = useMemo(() => {
    if (activeTicker) return activeTicker;
    const firstReady = tickers.find((t) => t.ready);
    return firstReady?.ticker ?? "";
  }, [activeTicker, tickers]);

  const { data: snapshot } = useSnapshot(effectiveTicker || null);
  const { data: candleRes } = useCandles(effectiveTicker || null);
  const { data: newsRes, error: newsError, isLoading: newsLoading } = useNews(
    effectiveTicker || null,
    NEWS_API_READY,
    newsDays
  );

  const fallbackName =
    tickers.find((t) => t.ticker === effectiveTicker)?.name ?? "종목";

  const dashView = useMemo(
    () => adaptSnapshot(snapshot ?? null, candleRes?.candles ?? [], fallbackName),
    [snapshot, candleRes, fallbackName]
  );

  const newsView = useMemo(
    () => adaptNews(newsRes, dashView.sentiScore, relativeTime),
    [newsRes, dashView.sentiScore]
  );

  const newsState: NewsState = !NEWS_API_READY
    ? "pending"
    : newsLoading
    ? "loading"
    : newsError
    ? "error"
    : "ready";

  const filteredArticles = useMemo(
    () =>
      newsView.articles.filter((n) => (newsFilter === "all" ? true : n.sentiment === newsFilter)),
    [newsView.articles, newsFilter]
  );

  const handleSelectTicker = useCallback((ticker: string) => {
    setActiveTicker(ticker);
    setNewsFilter("all");
    setNewsDays(30);
  }, []);

  // 스크리너 행 클릭 핸들러
  const handleScreenerSelect = useCallback(
    (code: string, _name: string, isTracked: boolean) => {
      handleSelectTicker(code);
      setView("home");
      if (!isTracked) {
        setToast("분석 데이터를 준비하고 있어요. 잠시 후 다시 확인해 주세요.");
      }
    },
    [handleSelectTicker]
  );

  // 사이드바 종목 클릭 핸들러 (is_tracked 모름 → 그냥 전환)
  const handleSidebarSelect = useCallback(
    (code: string) => {
      handleSelectTicker(code);
      setView("home");
    },
    [handleSelectTicker]
  );

  const isDetailView = view !== "screener";

  return (
    <div className="dashboard-bg min-h-screen flex" style={{ color: C.ink }}>
      {/* ── 데스크톱 사이드바 ── */}
      <Sidebar
        view={view}
        activeTicker={effectiveTicker}
        onViewChange={setView}
        onSelectTicker={handleSidebarSelect}
      />

      {/* ── 메인 영역 ── */}
      <main className="flex-1 min-w-0 px-5 sm:px-7 pt-7 pb-24 md:pb-16 max-w-[900px]">

        {/* 종목 헤더 — 상세 뷰일 때만 표시 */}
        {isDetailView && (
          <header className="rise d1 relative z-50 flex items-center justify-between gap-3 mb-4">
            <TickerSelector
              tickers={tickers}
              active={effectiveTicker}
              header={dashView.header}
              onSelect={handleSelectTicker}
              onSoon={(name) => setToast(`${name}은 데이터 준비 중이에요`)}
            />
            <StockHeader header={dashView.header} />
          </header>
        )}

        {/* 스크리너 뷰 */}
        {view === "screener" && (
          <div
            className="view-enter"
            key="view-screener"
            role="tabpanel"
            aria-labelledby="tab-screener"
          >
            <Screener onSelectTicker={handleScreenerSelect} />
          </div>
        )}

        {/* 종목 준비중 안내 */}
        {isDetailView && effectiveTicker && !dashView.ready && (
          <div
            className="rise d2 card-soft px-5 py-4 mb-5 flex items-center gap-3"
            style={{ background: C.amberTint, borderColor: `${C.amberSoft}66` }}
          >
            <span className="text-xl">🛠️</span>
            <p className="text-[13.5px] leading-relaxed" style={{ color: C.amber }}>
              <b>{dashView.header.name}</b>의 핵심 데이터를 준비하고 있어요. 일부 화면은 집계가 끝나면
              채워져요.
            </p>
          </div>
        )}

        {/* ── 홈 ── */}
        {view === "home" && (
          <div
            id="view-home"
            role="tabpanel"
            aria-labelledby="tab-home"
            className="view-enter"
            key={`home-${effectiveTicker}`}
          >
            <TrafficLightHero midSignal={dashView.midSignal} headline={dashView.headline} />
            <WhyCards cards={dashView.reasonCards} />
            <GapCompare gap={dashView.gap} />
            <CycleBar cycle={dashView.cycle} />
            <HorizonRows rows={dashView.horizons} />
            <LineChartWithMarkers chart={dashView.chart} />
            <EvidenceAccordion sections={dashView.evidence} />
            <AiReasonings items={dashView.aiReasonings} />
          </div>
        )}

        {/* ── 캔들 차트 ── */}
        {view === "chart" && (
          <div
            id="view-chart"
            role="tabpanel"
            aria-labelledby="tab-chart"
            className="view-enter"
            key={`chart-${effectiveTicker}`}
          >
            <CandleChart code={effectiveTicker} />
          </div>
        )}

        {/* ── 뉴스 ── */}
        {view === "news" && (
          <div
            id="view-news"
            role="tabpanel"
            aria-labelledby="tab-news"
            className="view-enter"
            key={`news-${effectiveTicker}`}
          >
            <NewsBanner sentiScore={newsView.sentiScore} analyzedCount={newsView.analyzedCount} />
            <NewsFilters active={newsFilter} onChange={setNewsFilter} days={newsDays} onDaysChange={setNewsDays} />
            <NewsList articles={filteredArticles} state={newsState} />
          </div>
        )}

        {/* ── 재무·공시 ── */}
        {view === "finance" && (
          <div
            id="view-finance"
            role="tabpanel"
            aria-labelledby="tab-finance"
            className="view-enter"
            key={`finance-${effectiveTicker}`}
          >
            <section className="rise d2 card relative overflow-hidden px-6 sm:px-8 py-7 mb-5">
              <div
                aria-hidden="true"
                className="absolute inset-x-0 -top-20 h-48 bg-gradient-to-b from-brand-amberTint/70 to-transparent pointer-events-none"
              />
              <div className="relative">
                <h2 className="text-[22px] sm:text-[26px] font-bold leading-snug tracking-[-0.01em]">
                  <span>{dashView.financeName}</span>,{" "}
                  <span style={{ color: C.amber }}>돈은 잘 벌고</span> 있을까요? 📊
                </h2>
                <p className="text-inkMuted text-sm sm:text-[15px] mt-2.5 leading-relaxed max-w-[46ch]">
                  어려운 재무 숫자를 쉬운 말로 풀어드릴게요. &quot;이 회사가 돈을 잘 버는지, 지금 주가가
                  비싼지&quot; 한눈에 살펴보세요.
                </p>
                <div className="flex flex-wrap items-center gap-2.5 mt-5">
                  <span
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
                    style={{ background: C.amberTint, border: `1px solid ${C.amberSoft}66` }}
                  >
                    <span className="text-base">🏛️</span>
                    <span className="font-bold text-sm" style={{ color: C.amber }}>
                      출처 · 금융감독원 전자공시(DART)
                    </span>
                  </span>
                  <span
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
                    style={{ background: "#EFF3F9" }}
                  >
                    <span className="text-base">🧾</span>
                    <span className="font-semibold text-sm text-inkMuted">공식 공시 문서 기반</span>
                  </span>
                </div>
              </div>
            </section>

            <FinanceCards cards={dashView.financeCards} />
            <FinanceBand band={dashView.financeBand} />
            <FinanceDisclosure dartUrl={dashView.dartUrl} />
          </div>
        )}

        <footer className="text-center text-faint text-xs mt-9" style={{ color: C.faint }}>
          본 화면은 투자 참고용이며 투자 권유가 아니에요. · Semi Senti
        </footer>
      </main>

      {/* ── 모바일 하단 탭바 ── */}
      <MobileTabBar view={view} onViewChange={setView} />

      {toast && <SoonToast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
