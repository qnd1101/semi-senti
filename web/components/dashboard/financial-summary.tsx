"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { FinancialSummaryDTO, Band } from "@/lib/types";

interface FinancialSummaryProps {
  financial: FinancialSummaryDTO;
  band?: Band;
  className?: string;
}

function fmt(value: number | null, opts?: Intl.NumberFormatOptions): string {
  if (value == null) return "-";
  return new Intl.NumberFormat("ko-KR", opts).format(value);
}

function fmtCompact(value: number | null): string {
  return fmt(value, { notation: "compact", maximumFractionDigits: 1 });
}

function fmtDecimal(value: number | null, digits = 2): string {
  return fmt(value, { maximumFractionDigits: digits });
}

const MESSAGES = {
  per: "PER",
  pbr: "PBR",
  eps: "EPS",
  revenue: "매출액",
  opIncome: "영업이익",
  bandLow: "밴드 하단",
  bandHigh: "밴드 상단",
} as const;

export function FinancialSummary({
  financial,
  band,
  className,
}: FinancialSummaryProps) {
  return (
    <div className={cn("grid grid-cols-2 gap-2 text-sm", className)}>
      <MetricCell label={MESSAGES.per} value={fmtDecimal(financial.per)} suffix="배" />
      <MetricCell label={MESSAGES.pbr} value={fmtDecimal(financial.pbr)} suffix="배" />
      <MetricCell label={MESSAGES.eps} value={fmtCompact(financial.eps)} suffix="원" />
      <MetricCell label={MESSAGES.revenue} value={fmtCompact(financial.revenue)} />
      <MetricCell label={MESSAGES.opIncome} value={fmtCompact(financial.operating_income)} />
      {band && band.band_low != null && band.band_high != null && (
        <>
          <MetricCell label={MESSAGES.bandLow} value={fmtCompact(band.band_low)} />
          <MetricCell label={MESSAGES.bandHigh} value={fmtCompact(band.band_high)} />
        </>
      )}
    </div>
  );
}

function MetricCell({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string;
  suffix?: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md bg-muted/30 px-2 py-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">
        {value}
        {suffix && value !== "-" && (
          <span className="ml-0.5 text-xs text-muted-foreground">{suffix}</span>
        )}
      </span>
    </div>
  );
}
