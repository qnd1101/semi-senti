"use client";

import * as React from "react";
import { AlertTriangle, Clock } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { StaleStatus } from "@/lib/types";

interface TopbarProps {
  stockName?: string;
  stockCode?: string;
  currentPrice?: number | null;
  currency?: string;
  baseDate?: string | null;
  stale?: StaleStatus;
  className?: string;
}

const MESSAGES = {
  noStock: "종목을 선택해주세요",
  staleWarning: "데이터 갱신 필요",
  baseDate: "기준일",
} as const;

function formatCurrency(value: number | null | undefined, currency = "KRW"): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  } catch {
    return dateStr;
  }
}

export function Topbar({
  stockName,
  stockCode,
  currentPrice,
  currency = "KRW",
  baseDate,
  stale,
  className,
}: TopbarProps) {
  const hasStock = Boolean(stockCode);

  return (
    <header
      className={cn(
        "flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/50 px-6",
        className
      )}
    >
      {/* Left: Stock Info */}
      <div className="flex items-center gap-4">
        {hasStock ? (
          <>
            <div className="flex items-baseline gap-2">
              <h1 className="text-lg font-semibold tracking-tight">
                {stockName}
              </h1>
              <span className="text-sm text-muted-foreground">
                ({stockCode})
              </span>
            </div>
            <div className="text-xl font-bold tabular-nums">
              {formatCurrency(currentPrice, currency)}
            </div>
          </>
        ) : (
          <span className="text-muted-foreground">{MESSAGES.noStock}</span>
        )}
      </div>

      {/* Right: Metadata & Status */}
      <div className="flex items-center gap-4">
        {baseDate && (
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              {MESSAGES.baseDate}: {formatDate(baseDate)}
            </span>
          </div>
        )}

        {stale?.is_stale && (
          <Badge variant="destructive" className="gap-1">
            <AlertTriangle className="h-3 w-3" />
            {MESSAGES.staleWarning}
          </Badge>
        )}
      </div>
    </header>
  );
}
