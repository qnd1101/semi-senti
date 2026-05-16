"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { DashboardSnapshot, SignalMarker } from "@/lib/types";
import { SentimentGauge } from "./sentiment-gauge";
import { KeywordTrend } from "./keyword-trend";
import { FinancialSummary } from "./financial-summary";
import { CyclePanel } from "./cycle-panel";
import { StaleBanner } from "./stale-banner";
import { DivergenceBadge } from "./divergence-badge";
import { SignalChart } from "./signal-chart";
import { SignalMarkerPopover } from "./signal-marker-popover";

interface DashboardShellProps {
  snapshot?: DashboardSnapshot | null;
  isLoading?: boolean;
  className?: string;
}

const MESSAGES = {
  noData: "종목을 선택하면 대시보드가 표시됩니다",
  chart: "시그널 차트",
  chartDesc: "캔들 + 펀더멘털 밴드 + BUY/SELL 마커",
  sentiment: "감성 지수",
  keywords: "주요 키워드",
  financial: "재무 요약",
  cycle: "업황 사이클",
} as const;

/**
 * DashboardShell — Semi Senti 메인 대시보드 그리드.
 *
 * PRD §4.3 1화면 집중:
 * - 좌(col-span-7, row-span-6): SignalChart
 * - 우(col-span-5): SentimentGauge / KeywordTrend / FinancialSummary / CyclePanel
 */
export function DashboardShell({
  snapshot,
  isLoading = false,
  className,
}: DashboardShellProps) {
  const [selectedMarker, setSelectedMarker] = React.useState<SignalMarker | null>(null);

  if (isLoading) {
    return <DashboardSkeleton className={className} />;
  }

  if (!snapshot) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center text-muted-foreground",
          className
        )}
      >
        {MESSAGES.noData}
      </div>
    );
  }

  const latestSignal = snapshot.signals.length > 0
    ? snapshot.signals[snapshot.signals.length - 1]
    : undefined;

  return (
    <div className={cn("flex h-full flex-col gap-4", className)}>
      {/* Stale Banner — 조건부 */}
      <StaleBanner stale={snapshot.stale} />

      {/* Main grid */}
      <div className="grid min-h-0 flex-1 grid-cols-12 grid-rows-6 gap-4">
        {/* Left: Signal Chart (col-span-7, row-span-6) */}
        <Card className="glass-card col-span-7 row-span-6 flex flex-col overflow-hidden">
          <CardHeader className="shrink-0 pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{MESSAGES.chart}</CardTitle>
              <div className="flex items-center gap-2">
                <DivergenceBadge divergences={snapshot.divergences} />
                {latestSignal && (
                  <Badge
                    variant={
                      latestSignal.kind === "BUY"
                        ? "buy"
                        : latestSignal.kind === "SELL"
                        ? "sell"
                        : "hold"
                    }
                  >
                    {latestSignal.kind}
                  </Badge>
                )}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">{MESSAGES.chartDesc}</p>
          </CardHeader>
          <CardContent className="relative min-h-0 flex-1 p-2">
            <SignalChart
              candles={snapshot.candles}
              signals={snapshot.signals}
              divergences={snapshot.divergences}
              band={snapshot.band}
              onMarkerClick={setSelectedMarker}
            />
            {/* Marker Popover — floating panel (optional) */}
            {selectedMarker && (
              <div className="absolute bottom-4 left-4 z-10">
                <SignalMarkerPopover marker={selectedMarker}>
                  <button
                    className="rounded-md border border-border bg-popover px-2 py-1 text-xs shadow-md"
                    onClick={() => setSelectedMarker(null)}
                  >
                    {selectedMarker.kind} — {selectedMarker.time.slice(0, 10)}
                    <span className="ml-1 text-muted-foreground">✕</span>
                  </button>
                </SignalMarkerPopover>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Stack: col-span-5 */}
        {/* Sentiment Gauge (row-span-2) */}
        <Card className="glass-card col-span-5 row-span-2 flex flex-col">
          <CardHeader className="shrink-0 pb-1">
            <CardTitle className="text-sm">{MESSAGES.sentiment}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-1 items-center justify-center p-2">
            <SentimentGauge sentiment={snapshot.sentiment} />
          </CardContent>
        </Card>

        {/* Keyword Trend (row-span-1) */}
        <Card className="glass-card col-span-5 row-span-1 flex flex-col">
          <CardHeader className="shrink-0 py-1.5">
            <CardTitle className="text-xs">{MESSAGES.keywords}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto px-3 py-1">
            <KeywordTrend keywords={snapshot.sentiment.top_keywords ?? []} />
          </CardContent>
        </Card>

        {/* Financial Summary (row-span-2) */}
        <Card className="glass-card col-span-5 row-span-2 flex flex-col">
          <CardHeader className="shrink-0 pb-1">
            <CardTitle className="text-sm">{MESSAGES.financial}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-3">
            <FinancialSummary
              financial={snapshot.financial}
              band={snapshot.band}
            />
          </CardContent>
        </Card>

        {/* Cycle Panel (row-span-1) */}
        <Card className="glass-card col-span-5 row-span-1 flex flex-col">
          <CardHeader className="shrink-0 py-1.5">
            <CardTitle className="text-xs">{MESSAGES.cycle}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-3">
            <CyclePanel cycle={snapshot.cycle} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DashboardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("grid h-full grid-cols-12 grid-rows-6 gap-4", className)}>
      <Skeleton className="col-span-7 row-span-6" />
      <Skeleton className="col-span-5 row-span-2" />
      <Skeleton className="col-span-5 row-span-1" />
      <Skeleton className="col-span-5 row-span-2" />
      <Skeleton className="col-span-5 row-span-1" />
    </div>
  );
}
