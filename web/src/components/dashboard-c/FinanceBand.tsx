import { C } from "@/lib/dashboard-c/tokens";
import { won } from "@/lib/dashboard-c/format";
import type { FinanceBandView } from "@/lib/dashboard-c/types";

export function FinanceBand({ band }: { band: FinanceBandView | null }) {
  return (
    <section className="rise d4 card px-6 sm:px-8 py-7 mb-5">
      <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
        <span className="text-xl">🎯</span> 지금 주가, 적정가랑 비교하면?
      </h2>
      <p className="text-inkMuted text-sm mb-6">
        회사 가치로 따져 본 합리적인 가격대(적정가 범위)와 지금 주가를 나란히 놓아봤어요.
      </p>
      {band ? <BandBody band={band} /> : <p className="text-faint text-sm py-4">적정가 밴드를 집계하고 있어요.</p>}
    </section>
  );
}

function BandBody({ band }: { band: FinanceBandView }) {
  const { low, high, current: cur, pos } = band;
  const expensive = pos >= 70;
  const markColor = expensive ? C.rose : C.emerald;
  const markRgb = expensive ? "229,72,77" : "14,159,110";
  const pillTint = expensive ? C.roseTint : C.emeraldTint;
  const pillText = expensive ? "조금 비싼 편" : "적정 수준";
  const verdictColor = expensive ? C.amber : C.emerald;
  const verdictTint = expensive ? C.amberTint : C.emeraldTint;
  const verdictText = expensive
    ? "👉 지금 주가는 적정가보다 조금 비싼 편이에요."
    : "👉 지금 주가는 적정가 범위 안이라 부담이 적은 편이에요.";

  const axisLow = low * 0.94;
  const axisHigh = high * 1.1;
  const toPct = (v: number) => Math.max(2, Math.min(98, ((v - axisLow) / (axisHigh - axisLow)) * 100));
  const bandLeft = toPct(low);
  const bandRight = toPct(high);
  const curLeft = toPct(cur);

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <span className="font-semibold text-sm flex items-center gap-1.5">
          <span className="text-base">📍</span> 현재가
          <b className="tnum ml-0.5" style={{ color: markColor }}>
            {won(cur)}원
          </b>
        </span>
        <span
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold"
          style={{ color: markColor, background: pillTint }}
        >
          {pillText} · 적정가 {pos}%
        </span>
      </div>
      <div className="relative h-12">
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-4 rounded-full" style={{ background: C.track }} />
        <div
          className="absolute top-1/2 -translate-y-1/2 h-4 rounded-full grow-x"
          style={{
            left: `${bandLeft}%`,
            width: `${bandRight - bandLeft}%`,
            background: `linear-gradient(90deg,${C.emeraldSoft},${C.emerald})`,
            transformOrigin: "left",
          }}
        />
        <div className="absolute top-0 bottom-0 flex flex-col items-center" style={{ left: `${curLeft}%`, transform: "translateX(-50%)" }}>
          <div className="w-[3px] flex-1 rounded-full" style={{ background: markColor }} />
          <div
            className="w-3.5 h-3.5 rounded-full border-2 border-white"
            style={{ background: markColor, boxShadow: `0 4px 10px -3px rgba(${markRgb},.6)`, marginTop: "-7px" }}
          />
        </div>
      </div>
      <div className="relative h-5 mt-1 text-[11px] font-semibold text-inkMuted tnum">
        <span className="absolute" style={{ left: `${bandLeft}%`, transform: "translateX(-50%)" }}>
          {won(low)}
        </span>
        <span className="absolute" style={{ left: `${bandRight}%`, transform: "translateX(-50%)" }}>
          {won(high)}
        </span>
      </div>
      <div className="flex items-center justify-center gap-4 text-xs mt-3">
        <span className="flex items-center gap-1.5 font-medium" style={{ color: C.emerald }}>
          <span className="w-3.5 h-[6px] rounded-full" style={{ background: C.emerald }} />
          적정가 범위
        </span>
        <span className="flex items-center gap-1.5 font-medium" style={{ color: markColor }}>
          <span className="w-[3px] h-3.5 rounded-full" style={{ background: markColor }} />
          현재가
        </span>
      </div>
      <p
        className="text-center text-sm font-semibold mt-4 px-4 py-2.5 rounded-2xl"
        style={{ color: verdictColor, background: verdictTint }}
      >
        {verdictText}
      </p>
    </div>
  );
}
