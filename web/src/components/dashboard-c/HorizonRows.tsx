import { C, type SignalType } from "@/lib/dashboard-c/tokens";
import type { HorizonRow } from "@/lib/dashboard-c/types";

const MAP: Record<SignalType, { c: string; tint: string; emoji: string; verb: string }> = {
  SELL: { c: C.rose, tint: C.roseTint, emoji: "🛑", verb: "지금은 팔기" },
  HOLD: { c: C.amber, tint: C.amberTint, emoji: "✋", verb: "기다리기" },
  BUY: { c: C.emerald, tint: C.emeraldTint, emoji: "🌱", verb: "사도 좋아요" },
};

export function HorizonRows({ rows }: { rows: HorizonRow[] }) {
  return (
    <section className="rise d5 card px-6 sm:px-8 py-7 mb-5">
      <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
        <span className="text-xl">🗓️</span> 기간별로 보면 이래요
      </h2>
      <p className="text-inkMuted text-sm mb-5">얼마나 오래 들고 갈 생각인지에 따라 답이 달라요.</p>
      <div className="space-y-2.5">
        {rows.map((r) => {
          const m = r.signal ? MAP[r.signal] : null;
          return (
            <div
              key={r.sub}
              className="flex items-center gap-3.5 rounded-2xl px-4 py-3.5"
              style={{ background: m ? `${m.tint}40` : `${C.track}80` }}
            >
              <span
                className="w-10 h-10 rounded-xl grid place-items-center text-xl shrink-0"
                style={{ background: C.white, boxShadow: "0 2px 8px -4px rgba(26,43,69,.2)" }}
              >
                {m ? m.emoji : "⏳"}
              </span>
              <div className="min-w-0">
                <div className="font-bold text-[15px] leading-tight">
                  {r.when}
                  <span className="text-faint text-xs font-medium ml-1">{r.sub}</span>
                </div>
                <div className="text-sm font-semibold mt-0.5" style={{ color: m ? m.c : C.muted }}>
                  {m ? m.verb : "집계 중"}
                </div>
              </div>
              {r.signal && (
                <span
                  className="ml-auto text-[11px] font-medium px-2 py-1 rounded-md tnum"
                  style={{ color: m!.c, background: C.white }}
                >
                  {r.signal}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
