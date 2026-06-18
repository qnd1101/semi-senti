import { C } from "@/lib/dashboard-c/tokens";
import type { FinanceCard } from "@/lib/dashboard-c/types";

export function FinanceCards({ cards }: { cards: FinanceCard[] }) {
  return (
    <div className="rise d3 mb-5">
      <h2 className="text-lg font-bold mb-3 px-1 flex items-center gap-2">
        <span className="text-xl">💵</span> 핵심 재무, 쉽게 풀어봤어요
      </h2>
      {cards.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {cards.map((c) => (
            <div
              key={c.label}
              className="card-soft p-5 flex items-start gap-4"
              style={{ borderColor: `color-mix(in srgb, ${c.accent} 14%, ${C.line})` }}
            >
              <div
                className="w-12 h-12 rounded-2xl grid place-items-center text-[24px] shrink-0"
                style={{ background: c.tint }}
              >
                {c.emoji}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-faint text-[12px] font-semibold mb-0.5">{c.label}</div>
                <div className="font-bold text-[22px] tnum leading-tight" style={{ color: c.accent }}>
                  {c.value}
                </div>
                <p className="text-inkMuted text-[12.5px] leading-relaxed mt-1.5">{c.easy}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card-soft p-6 text-center text-faint text-sm">
          재무 데이터를 준비하고 있어요.
        </div>
      )}
    </div>
  );
}
