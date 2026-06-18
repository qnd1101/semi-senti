import { C, type SignalType } from "@/lib/dashboard-c/tokens";
import type { HeadlineView } from "@/lib/dashboard-c/types";

interface Lamp {
  key: SignalType;
  color: string;
  glow: string;
  emoji: string;
  label: string;
  accent: string;
}

const LAMPS: Lamp[] = [
  { key: "SELL", color: C.rose, glow: "rgba(229,72,77,0.32)", emoji: "🛑", label: "팔기", accent: C.rose },
  { key: "HOLD", color: C.amberSoft, glow: "rgba(245,181,68,0.45)", emoji: "✋", label: "기다리기", accent: C.amber },
  { key: "BUY", color: C.emerald, glow: "rgba(14,159,110,0.30)", emoji: "🌱", label: "사기", accent: C.emerald },
];

const ACCENT_COLOR: Record<HeadlineView["accentColor"], string> = {
  emerald: C.emerald,
  rose: C.rose,
  amber: C.amber,
  muted: C.muted,
};

export function TrafficLightHero({
  midSignal,
  headline,
}: {
  midSignal: SignalType | null;
  headline: HeadlineView | null;
}) {
  return (
    <section className="rise d2 card relative overflow-hidden px-6 sm:px-9 pt-9 pb-8 mb-5 text-center">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 -top-24 h-56 bg-gradient-to-b from-brand-amberTint/70 to-transparent pointer-events-none"
      />
      <div className="relative">
        {/* 신호등 본체 */}
        <div className="inline-flex items-center justify-center gap-5 sm:gap-7 mb-7">
          {LAMPS.map((l) => {
            const active = midSignal === l.key;
            if (active) {
              return (
                <div key={l.key} className="flex flex-col items-center gap-2">
                  <div
                    className="lamp-active lamp-breathe w-[78px] h-[78px] sm:w-[92px] sm:h-[92px] rounded-full grid place-items-center text-[34px] sm:text-[40px]"
                    style={{ background: l.color, ["--glow" as string]: l.glow }}
                  >
                    {l.emoji}
                  </div>
                  <span className="text-sm font-bold" style={{ color: l.accent }}>
                    {l.label}
                  </span>
                </div>
              );
            }
            return (
              <div key={l.key} className="flex flex-col items-center gap-2">
                <div
                  className="w-[58px] h-[58px] sm:w-[66px] sm:h-[66px] rounded-full grid place-items-center text-[24px] sm:text-[26px] grayscale opacity-35"
                  style={{ background: C.track }}
                >
                  {l.emoji}
                </div>
                <span className="text-xs font-medium text-faint">{l.label}</span>
              </div>
            );
          })}
        </div>

        {/* 행동 헤드라인 */}
        {headline ? (
          <>
            <h1 className="text-[30px] sm:text-[38px] font-bold leading-[1.15] tracking-[-0.02em]">
              {headline.lead}{" "}
              <span style={{ color: ACCENT_COLOR[headline.accentColor] }}>{headline.accent}</span>{" "}
              {headline.tail}
            </h1>
            <p className="text-inkMuted text-[15px] sm:text-base mt-3 leading-relaxed max-w-[34ch] mx-auto">
              {headline.sub}
            </p>
            <div
              className="inline-flex items-center gap-2 mt-5 px-4 py-2 rounded-full"
              style={{ background: headline.badge.tint, border: `1px solid ${headline.badge.dotColor}66` }}
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: headline.badge.dotColor }} />
              <span className="font-bold text-sm" style={{ color: headline.badge.textColor }}>
                {headline.badge.text}
              </span>
              <span className="text-faint text-xs font-medium">{headline.badge.meta}</span>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-[28px] sm:text-[34px] font-bold leading-[1.15] tracking-[-0.02em] text-inkMuted">
              판단을 준비하고 있어요
            </h1>
            <p className="text-inkMuted text-[15px] mt-3 leading-relaxed max-w-[34ch] mx-auto">
              이 종목의 신호를 모으는 중이에요. 잠시 후 다시 확인해 주세요.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
