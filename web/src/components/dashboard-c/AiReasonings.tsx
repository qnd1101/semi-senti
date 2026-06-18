import { C } from "@/lib/dashboard-c/tokens";
import type { AiReasoning } from "@/lib/dashboard-c/types";
import { Chevron } from "./Chevron";

const HORIZON_STYLE: Record<
  "short" | "mid" | "long",
  { emoji: string; color: string; tint: string }
> = {
  short: { emoji: "⚡", color: C.amber, tint: C.amberTint },
  mid: { emoji: "🔭", color: C.emerald, tint: C.emeraldTint },
  long: { emoji: "🌏", color: "#2563EB", tint: "#E8EFFD" },
};

export function AiReasonings({ items }: { items: AiReasoning[] }) {
  if (items.length === 0) return null;

  return (
    <section className="rise d7 mb-3">
      <h2 className="text-lg font-bold mb-1 px-1 flex items-center gap-2">
        <span className="text-xl">🤖</span> AI 분석 근거
      </h2>
      <p className="text-[13px] text-inkMuted mb-3 px-1 leading-relaxed">
        AI가 데이터를 읽고 직접 작성한 설명이에요
      </p>
      <div className="space-y-2.5">
        {items.map((item, i) => {
          const style = HORIZON_STYLE[item.horizon];
          return (
            <details
              key={item.horizon}
              className="card-soft overflow-hidden"
              open={i === 0}
            >
              <summary className="flex items-center gap-3 px-5 py-4 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                <span
                  className="w-10 h-10 rounded-xl grid place-items-center text-lg shrink-0"
                  style={{ background: style.tint }}
                >
                  {style.emoji}
                </span>
                <span className="flex-1">
                  <span className="font-bold text-[15px]">{item.label} 관점</span>
                </span>
                <Chevron className="acc-chevron w-5 h-5 text-faint shrink-0" />
              </summary>
              <div className="acc-body">
                <div className="px-5 pb-5 pt-0">
                  <p
                    className="text-[13.5px] leading-relaxed"
                    style={{ color: C.ink }}
                  >
                    {item.text}
                  </p>
                </div>
              </div>
            </details>
          );
        })}
      </div>
      <p
        className="text-[11.5px] mt-3 px-1 leading-relaxed"
        style={{ color: C.faint }}
      >
        AI 생성 내용으로 투자 조언이 아니며 오류가 있을 수 있어요.
      </p>
    </section>
  );
}
