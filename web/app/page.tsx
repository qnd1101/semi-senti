"use client";

import * as React from "react";
import { AppShell } from "@/components/layout";
import { DashboardShell, StockSelector } from "@/components/dashboard";
import type { DashboardSnapshot, Stock, StaleStatus } from "@/lib/types";

/**
 * Semi Senti — 메인 대시보드 페이지.
 *
 * Phase 5 T-050: AppShell + DashboardShell 골격 구현.
 *
 * 현재는 mock 데이터로 UI 구조를 검증하며,
 * T-053/T-054에서 실제 API + SWR hook으로 교체 예정.
 */

const MOCK_STOCKS: Stock[] = [
  { stock_code: "005930", name: "삼성전자", market: "KOSPI", is_active: true },
  { stock_code: "000660", name: "SK하이닉스", market: "KOSPI", is_active: true },
  { stock_code: "042700", name: "한미반도체", market: "KOSDAQ", is_active: true },
];

const MOCK_STALE: StaleStatus = {
  is_stale: false,
  last_updated: "2026-05-17T03:00:00+09:00",
  hours_old: 0.5,
  message: "데이터가 최신 상태입니다",
};

const MOCK_SNAPSHOT: DashboardSnapshot = {
  stock_code: "005930",
  stock_name: "삼성전자",
  candles: [],
  signals: [
    {
      time: "2026-05-16T09:00:00+09:00",
      kind: "HOLD",
      price: 72000,
      reason: "현재가가 밴드 내 위치 · 감성 중립",
      sentiment_score: 15,
    },
  ],
  divergences: [],
  sentiment: {
    score: 15,
    bucket: "NEUTRAL",
    bucket_label_ko: "중립",
    history: [],
    top_keywords: [
      { keyword: "HBM", weight: 2.5, count: 42 },
      { keyword: "파운드리", weight: 1.8, count: 28 },
      { keyword: "수율", weight: 1.5, count: 15 },
      { keyword: "재고", weight: -1.2, count: 12 },
      { keyword: "수요", weight: 1.0, count: 10 },
    ],
    updated_at: "2026-05-17T03:00:00+09:00",
  },
  financial: {
    current_price: 72000,
    currency: "KRW",
    record_date: "2026-05-16",
    revenue: 74500000000000,
    operating_income: 6400000000000,
    per: 12.5,
    pbr: 1.1,
    eps: 5760,
  },
  band: {
    band_high: 85000,
    band_low: 62000,
    method: "PER/PBR 기반",
  },
  cycle: {
    score: 65,
    label: "회복기",
    inventory_turnover: 5.2,
    yoy_revenue: 15.3,
    updated_at: "2026-05-17T03:00:00+09:00",
  },
  stale: MOCK_STALE,
  generated_at: "2026-05-17T03:00:00+09:00",
};

export default function HomePage() {
  const [selectedCode, setSelectedCode] = React.useState<string>("005930");

  const selectedStock = React.useMemo(
    () => MOCK_STOCKS.find((s) => s.stock_code === selectedCode),
    [selectedCode]
  );

  const snapshot = selectedCode ? MOCK_SNAPSHOT : null;

  return (
    <AppShell
      stockName={selectedStock?.name}
      stockCode={selectedCode}
      currentPrice={snapshot?.financial.current_price}
      currency={snapshot?.financial.currency}
      baseDate={snapshot?.financial.record_date}
      stale={snapshot?.stale}
      sidebarContent={
        <StockSelector
          stocks={MOCK_STOCKS}
          value={selectedCode}
          onValueChange={setSelectedCode}
        />
      }
    >
      <DashboardShell snapshot={snapshot} />
    </AppShell>
  );
}
