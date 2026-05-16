"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { CycleScore } from "@/lib/types";

interface CyclePanelProps {
  cycle: CycleScore | null | undefined;
  className?: string;
}

const MESSAGES = {
  noData: "사이클 분석 결과 없음",
  score: "점수",
} as const;

function getCycleColor(score: number | null): string {
  if (score == null) return "bg-muted";
  if (score >= 75) return "bg-signal-sell";
  if (score >= 50) return "bg-divergence-bullish";
  if (score >= 25) return "bg-signal-buy";
  return "bg-divergence-bearish";
}

export function CyclePanel({ cycle, className }: CyclePanelProps) {
  if (!cycle || cycle.score == null) {
    return (
      <p className={cn("text-xs text-muted-foreground", className)}>
        {MESSAGES.noData}
      </p>
    );
  }

  const pct = Math.max(0, Math.min(100, cycle.score));

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{cycle.label}</span>
        <span className="tabular-nums text-muted-foreground">
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", getCycleColor(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
      {(cycle.inventory_turnover != null || cycle.yoy_revenue != null) && (
        <div className="flex gap-3 text-xs text-muted-foreground">
          {cycle.inventory_turnover != null && (
            <span>
              재고회전{" "}
              <span className="font-medium text-foreground">
                {cycle.inventory_turnover.toFixed(1)}
              </span>
            </span>
          )}
          {cycle.yoy_revenue != null && (
            <span>
              YoY 매출{" "}
              <span className="font-medium text-foreground">
                {cycle.yoy_revenue >= 0 ? "+" : ""}
                {cycle.yoy_revenue.toFixed(1)}%
              </span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
