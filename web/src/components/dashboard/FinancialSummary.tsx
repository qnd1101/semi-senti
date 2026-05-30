"use client";

import { formatNumber } from "@/lib/classify-sentiment";
import type { FinancialInfo, PriceInfo } from "@/lib/types";

interface Props {
  price: PriceInfo;
  financials: FinancialInfo;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-zinc-800/60">
      <span className="text-xs text-zinc-400">{label}</span>
      <span className="text-xs tabular-nums text-zinc-200">{value}</span>
    </div>
  );
}

export function FinancialSummary({ price, financials }: Props) {
  const bp = price.band_pos_pct;
  const bandLabel = bp === null ? "—" : bp < 30 ? "저평가" : bp > 70 ? "고평가" : "중립";
  const bandColor = bp === null ? "text-zinc-400" : bp < 30 ? "text-emerald-400" : bp > 70 ? "text-rose-400" : "text-zinc-400";

  return (
    <div className="flex flex-col gap-1">
      <Row label="현재가" value={`₩${formatNumber(price.close)}`} />
      <Row label="밴드 하단" value={`₩${formatNumber(price.band_low)}`} />
      <Row label="밴드 상단" value={`₩${formatNumber(price.band_high)}`} />
      <div className="flex justify-between items-center py-1 border-b border-zinc-800/60">
        <span className="text-xs text-zinc-400">밴드 위치</span>
        <span className={`text-xs tabular-nums ${bandColor}`}>
          {bp !== null ? `${bp.toFixed(1)}%` : "—"} ({bandLabel})
        </span>
      </div>
      <Row label="매출액" value={financials.revenue ? `${formatNumber(financials.revenue / 1e8)}억` : "—"} />
      <Row label="영업이익" value={financials.operating_profit ? `${formatNumber(financials.operating_profit / 1e8)}억` : "—"} />
      <Row label="PER" value={financials.per ? `${financials.per.toFixed(1)}x` : "—"} />
      <Row label="PBR" value={financials.pbr ? `${financials.pbr.toFixed(2)}x` : "—"} />
      <Row label="EPS" value={financials.eps ? `₩${formatNumber(financials.eps)}` : "—"} />
    </div>
  );
}
