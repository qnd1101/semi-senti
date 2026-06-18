import { C, sentimentMood } from "@/lib/dashboard-c/tokens";
import type { GapCompareView } from "@/lib/dashboard-c/types";
import { sentiFmt, bandPosFmt } from "@/lib/dashboard-c/format";

export function GapCompare({ gap }: { gap: GapCompareView | null }) {
  return (
    <section className="rise d4 card px-6 sm:px-8 py-7 mb-5">
      <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
        <span className="text-xl">⚖️</span> 분위기랑 가격, 따로 노네요
      </h2>
      <p className="text-inkMuted text-sm mb-6">
        뉴스 분위기와 주가 위치를 나란히 놓아봤어요. 차이가 클수록 신중해야 해요.
      </p>
      {gap ? (
        <GapBody gap={gap} />
      ) : (
        <p className="text-faint text-sm py-4">분위기·가격 데이터를 집계하고 있어요.</p>
      )}
    </section>
  );
}

function GapBody({ gap }: { gap: GapCompareView }) {
  const pricePct = gap.pricePct ?? 0;
  const expensive = gap.expensive;
  const priceWord = expensive ? "비쌈" : "적정";
  const priceColor = expensive ? C.rose : C.emerald;
  const priceGrad = expensive ? `${C.roseSoft},${C.rose}` : `${C.emeraldSoft},${C.emerald}`;
  const score = gap.sentiScore;
  const mood = sentimentMood(score);
  const sentiGrad = mood.cold
    ? `${C.roseSoft},${C.rose}`
    : mood.warm
    ? `${C.emeraldSoft},${C.emerald}`
    : `${C.faint},${C.muted}`;

  return (
    <div className="space-y-5">
      {/* 뉴스 분위기 바 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-sm flex items-center gap-1.5">
            <span className="text-base">{mood.emoji}</span> 뉴스 분위기
          </span>
          <span className="font-bold text-sm" style={{ color: mood.color }}>
            {mood.label} · {score != null ? sentiFmt(score) : "—"}
          </span>
        </div>
        <div className="h-4 rounded-full overflow-hidden" style={{ background: C.track }}>
          <div
            className="h-full rounded-full grow-x"
            style={{ width: `${gap.sentiPct}%`, background: `linear-gradient(90deg,${sentiGrad})` }}
          />
        </div>
      </div>
      {/* 주가 위치 바 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-sm flex items-center gap-1.5">
            <span className="text-base">💰</span> 주가 위치
          </span>
          <span className="font-bold text-sm" style={{ color: priceColor }}>
            {priceWord} · {bandPosFmt(pricePct)}%
          </span>
        </div>
        <div className="h-4 rounded-full overflow-hidden" style={{ background: C.track }}>
          <div
            className="h-full rounded-full grow-x"
            style={{ width: `${pricePct}%`, background: `linear-gradient(90deg,${priceGrad})`, animationDelay: "0.78s" }}
          />
        </div>
      </div>
      {/* 결론 라벨 */}
      <div className="flex items-center justify-center gap-2.5 pt-1">
        <span className="h-px flex-1 max-w-[80px]" style={{ background: C.line }} />
        <span
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-bold"
          style={{ color: gap.verdict.color, background: gap.verdict.tint }}
        >
          <span>👉</span> {gap.verdict.text}
        </span>
        <span className="h-px flex-1 max-w-[80px]" style={{ background: C.line }} />
      </div>
    </div>
  );
}
