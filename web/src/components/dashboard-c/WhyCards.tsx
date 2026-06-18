import { C } from "@/lib/dashboard-c/tokens";
import type { ReasonCard } from "@/lib/dashboard-c/types";

export function WhyCards({ cards }: { cards: ReasonCard[] }) {
  return (
    <div className="rise d3 mb-5">
      <h2 className="text-lg font-bold mb-3 px-1 flex items-center gap-2">
        <span className="text-xl">🤔</span> 왜 이렇게 보는 걸까요?
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {cards.map((c, i) => (
          <div
            key={i}
            className="card-soft p-5 flex flex-col h-full"
            style={{ borderColor: `color-mix(in srgb, ${c.accent} 14%, ${C.line})` }}
          >
            <div
              className="w-12 h-12 rounded-2xl grid place-items-center text-[24px] mb-3.5"
              style={{ background: c.tint }}
            >
              {c.emoji}
            </div>
            <h3 className="font-bold text-[15px] leading-snug mb-1.5">{c.title}</h3>
            <p className="text-inkMuted text-[13px] leading-relaxed mb-4 flex-1">{c.desc}</p>
            <div className="pt-3 border-t" style={{ borderColor: C.line }}>
              <div className="font-bold text-lg tnum leading-none" style={{ color: c.accent }}>
                {c.stat}
              </div>
              <div className="text-faint text-[11px] mt-1">{c.statLabel}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
