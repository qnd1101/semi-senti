"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { DashboardSnapshot } from "@/lib/types";

interface DashboardShellProps {
  snapshot?: DashboardSnapshot | null;
  isLoading?: boolean;
  className?: string;
}

const MESSAGES = {
  noData: "종목을 선택하면 대시보드가 표시됩니다",
  chart: "시그널 차트",
  chartDesc: "캔들 + 펀더멘털 밴드 + BUY/SELL/Divergence 마커",
  sentiment: "감성 지수",
  keywords: "주요 키워드",
  financial: "재무 요약",
  cycle: "업황 사이클",
} as const;

/**
 * DashboardShell — Semi Senti 메인 대시보드 그리드.
 *
 * 그리드 구조 (PRD §4.3 1화면 집중):
 * ┌─────────────────────────────────┬─────────────────┐
 * │                                 │ SentimentGauge  │
 * │                                 │ (row-span-2)    │
 * │      SignalChartCard            ├─────────────────│
 * │      (col-span-7, row-span-6)   │ KeywordTrend    │
 * │                                 │ (row-span-1)    │
 * │                                 ├─────────────────│
 * │                                 │ FinancialSummary│
 * │                                 │ (row-span-2)    │
 * │                                 ├─────────────────│
 * │                                 │ CyclePanel      │
 * │                                 │ (row-span-1)    │
 * └─────────────────────────────────┴─────────────────┘
 *
 * 현재는 placeholder 박스로 채워두고, T-055/T-056에서 실제 컴포넌트로 교체.
 */
export function DashboardShell({
  snapshot,
  isLoading = false,
  className,
}: DashboardShellProps) {
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

  return (
    <div
      className={cn(
        "grid h-full grid-cols-12 grid-rows-6 gap-4",
        className
      )}
    >
      {/* Left: Signal Chart (col-span-7, row-span-6) */}
      <Card className="glass-card col-span-7 row-span-6 flex flex-col">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{MESSAGES.chart}</CardTitle>
            <div className="flex items-center gap-2">
              {snapshot.signals.length > 0 && (
                <Badge
                  variant={
                    snapshot.signals[snapshot.signals.length - 1]?.kind === "BUY"
                      ? "buy"
                      : snapshot.signals[snapshot.signals.length - 1]?.kind === "SELL"
                      ? "sell"
                      : "hold"
                  }
                >
                  {snapshot.signals[snapshot.signals.length - 1]?.kind}
                </Badge>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">{MESSAGES.chartDesc}</p>
        </CardHeader>
        <CardContent className="flex-1 p-4">
          {/* T-056: SignalChart 컴포넌트 삽입 영역 */}
          <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-border bg-muted/20">
            <div className="text-center text-sm text-muted-foreground">
              <p className="font-medium">SignalChart</p>
              <p className="text-xs">T-056에서 구현 예정</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Right Stack: col-span-5 */}
      {/* Sentiment Gauge (row-span-2) */}
      <Card className="glass-card col-span-5 row-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{MESSAGES.sentiment}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-full flex-col items-center justify-center gap-2">
            {/* T-055: SentimentGauge 컴포넌트 삽입 영역 */}
            <div className="flex h-20 w-full items-center justify-center rounded-lg border border-dashed border-border bg-muted/20">
              <span className="text-sm text-muted-foreground">
                SentimentGauge (T-055)
              </span>
            </div>
            <div className="flex items-center gap-2 text-2xl font-bold tabular-nums">
              <span
                className={cn(
                  snapshot.sentiment.bucket === "GREED" && "text-signal-buy",
                  snapshot.sentiment.bucket === "FEAR" && "text-signal-sell",
                  snapshot.sentiment.bucket === "NEUTRAL" && "text-signal-hold"
                )}
              >
                {snapshot.sentiment.score ?? "-"}
              </span>
              <Badge
                variant={
                  snapshot.sentiment.bucket === "GREED"
                    ? "buy"
                    : snapshot.sentiment.bucket === "FEAR"
                    ? "sell"
                    : "hold"
                }
              >
                {snapshot.sentiment.bucket_label_ko}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Keyword Trend (row-span-1) */}
      <Card className="glass-card col-span-5 row-span-1">
        <CardHeader className="py-2">
          <CardTitle className="text-sm">{MESSAGES.keywords}</CardTitle>
        </CardHeader>
        <CardContent className="py-2">
          {/* T-055: KeywordTrend 컴포넌트 삽입 영역 */}
          <div className="flex flex-wrap gap-1">
            {snapshot.sentiment.top_keywords?.slice(0, 5).map((kw) => (
              <Badge
                key={kw.keyword}
                variant="secondary"
                className="text-xs"
              >
                {kw.keyword}
              </Badge>
            )) ?? (
              <span className="text-xs text-muted-foreground">
                키워드 없음
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Financial Summary (row-span-2) */}
      <Card className="glass-card col-span-5 row-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{MESSAGES.financial}</CardTitle>
        </CardHeader>
        <CardContent>
          {/* T-055: FinancialSummary 컴포넌트 삽입 영역 */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <FinancialItem
              label="PER"
              value={snapshot.financial.per}
              suffix="배"
            />
            <FinancialItem
              label="PBR"
              value={snapshot.financial.pbr}
              suffix="배"
            />
            <FinancialItem
              label="EPS"
              value={snapshot.financial.eps}
              suffix="원"
            />
            <FinancialItem
              label="매출액"
              value={snapshot.financial.revenue}
              format="compact"
            />
          </div>
        </CardContent>
      </Card>

      {/* Cycle Panel (row-span-1) */}
      <Card className="glass-card col-span-5 row-span-1">
        <CardHeader className="py-2">
          <CardTitle className="text-sm">{MESSAGES.cycle}</CardTitle>
        </CardHeader>
        <CardContent className="py-2">
          {/* T-055: CyclePanel 컴포넌트 삽입 영역 */}
          {snapshot.cycle ? (
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-signal-buy transition-all"
                    style={{ width: `${snapshot.cycle.score ?? 0}%` }}
                  />
                </div>
              </div>
              <span className="min-w-[4rem] text-right text-sm font-medium">
                {snapshot.cycle.label}
              </span>
            </div>
          ) : (
            <span className="text-xs text-muted-foreground">
              사이클 데이터 없음
            </span>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FinancialItem({
  label,
  value,
  suffix,
  format,
}: {
  label: string;
  value: number | null;
  suffix?: string;
  format?: "compact";
}) {
  const formatted = React.useMemo(() => {
    if (value == null) return "-";
    if (format === "compact") {
      return new Intl.NumberFormat("ko-KR", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value);
    }
    return new Intl.NumberFormat("ko-KR", {
      maximumFractionDigits: 2,
    }).format(value);
  }, [value, format]);

  return (
    <div className="flex items-center justify-between rounded-md bg-muted/30 px-2 py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">
        {formatted}
        {suffix && value != null && (
          <span className="ml-0.5 text-xs text-muted-foreground">{suffix}</span>
        )}
      </span>
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
