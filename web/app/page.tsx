"use client";

import * as React from "react";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "@/components/layout";
import { DashboardShell, StockSelector } from "@/components/dashboard";
import { useAutoRefresh, useSnapshot, useStocks } from "@/hooks";

/**
 * Semi Senti — 메인 대시보드.
 *
 * T-051~T-054: sql.js DB + snapshot 빌더 + Route Handler + SWR 훅.
 */

function HomePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const paramCode = searchParams.get("code");

  const { data: stocks, isLoading: stocksLoading } = useStocks();
  const auto = useAutoRefresh();

  const selectedCode = React.useMemo(() => {
    if (!stocks?.length) return "";
    if (paramCode && stocks.some((s) => s.stock_code === paramCode)) {
      return paramCode;
    }
    return stocks[0]!.stock_code;
  }, [stocks, paramCode]);

  React.useEffect(() => {
    if (!stocks?.length || !selectedCode) return;
    if (paramCode !== selectedCode) {
      router.replace(`/?code=${encodeURIComponent(selectedCode)}`, {
        scroll: false,
      });
    }
  }, [stocks, selectedCode, paramCode, router]);

  const {
    data: snapshot,
    isLoading: snapLoading,
    error: snapshotError,
  } = useSnapshot(selectedCode || null, auto.refreshIntervalMs);

  const selectedStock = stocks?.find((s) => s.stock_code === selectedCode);

  const handleStockChange = (code: string) => {
    router.replace(`/?code=${encodeURIComponent(code)}`, { scroll: false });
  };

  const showLoading = stocksLoading || (Boolean(selectedCode) && snapLoading);

  return (
    <AppShell
      stockName={selectedStock?.name ?? snapshot?.stock_name}
      stockCode={selectedCode || undefined}
      currentPrice={snapshot?.financial.current_price}
      currency={snapshot?.financial.currency}
      baseDate={snapshot?.financial.record_date}
      stale={snapshot?.stale}
      sidebarAutoRefreshEnabled={auto.enabled}
      onSidebarAutoRefreshChange={auto.setEnabled}
      sidebarPollMinutes={auto.pollMinutes}
      onSidebarPollMinutesChange={auto.setPollMinutes}
      sidebarContent={
        stocksLoading ? (
          <p className="text-sm text-muted-foreground">종목 목록을 불러오는 중…</p>
        ) : (
          <StockSelector
            stocks={stocks ?? []}
            value={selectedCode || undefined}
            onValueChange={handleStockChange}
          />
        )
      }
    >
      {snapshotError != null && (
        <p className="mb-2 text-sm text-destructive" role="alert">
          스냅샷을 불러오지 못했습니다. DB 경로와 서버 로그를 확인해 주세요.
        </p>
      )}
      <DashboardShell snapshot={snapshot ?? null} isLoading={showLoading} />
    </AppShell>
  );
}

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center text-muted-foreground">
          로딩 중…
        </div>
      }
    >
      <HomePageInner />
    </Suspense>
  );
}
