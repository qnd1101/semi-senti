"use client";

import type { CycleInfo } from "@/lib/types";

const PHASE_LABEL: Record<string, string> = {
  TROUGH: "저점",
  EARLY_CYCLE: "초기 회복",
  MID_CYCLE: "중기 확장",
  LATE_CYCLE: "후기 과열",
  PEAK: "고점",
};

const PHASE_COLOR: Record<string, string> = {
  TROUGH: "#f43f5e",
  EARLY_CYCLE: "#fb923c",
  MID_CYCLE: "#4ade80",
  LATE_CYCLE: "#facc15",
  PEAK: "#fb7185",
};

interface Props {
  cycle: CycleInfo | null;
}

export function CyclePanel({ cycle }: Props) {
  if (!cycle) return <p className="text-xs text-zinc-500">업황 사이클 데이터 없음</p>;

  const pct = ((cycle.cycle_score + 100) / 200) * 100;
  const color = PHASE_COLOR[cycle.phase] || "#71717a";
  const label = PHASE_LABEL[cycle.phase] || cycle.phase;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color }}>{label}</span>
        <span className="text-xs tabular-nums text-zinc-300">{cycle.cycle_score.toFixed(1)}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-zinc-800 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct.toFixed(1)}%`, background: color }}
        />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
        {cycle.inventory_turnover !== null && (
          <>
            <span className="text-xs text-zinc-500">재고 회전율</span>
            <span className="text-xs tabular-nums text-zinc-300">{cycle.inventory_turnover?.toFixed(2)}회</span>
          </>
        )}
        {cycle.revenue_growth_pct !== null && (
          <>
            <span className="text-xs text-zinc-500">YoY 매출 성장</span>
            <span className="text-xs tabular-nums text-zinc-300">{cycle.revenue_growth_pct?.toFixed(1)}%</span>
          </>
        )}
        {cycle.op_margin_pct !== null && (
          <>
            <span className="text-xs text-zinc-500">영업이익률</span>
            <span className="text-xs tabular-nums text-zinc-300">{cycle.op_margin_pct?.toFixed(1)}%</span>
          </>
        )}
      </div>
      <span className="text-[10px] text-zinc-600">{cycle.score_date}</span>
    </div>
  );
}
