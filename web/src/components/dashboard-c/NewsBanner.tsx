import { C, sentimentMood } from "@/lib/dashboard-c/tokens";
import { sentiFmt } from "@/lib/dashboard-c/format";

export function NewsBanner({
  sentiScore,
  analyzedCount,
}: {
  sentiScore: number | null;
  analyzedCount: number | null;
}) {
  const mood = sentimentMood(sentiScore);
  return (
    <section className="rise d2 card relative overflow-hidden px-6 sm:px-8 py-7 mb-5">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 -top-20 h-48 bg-gradient-to-b from-brand-emeraldTint/70 to-transparent pointer-events-none"
      />
      <div className="relative">
        <h2 className="text-[22px] sm:text-[26px] font-bold leading-snug tracking-[-0.01em]">
          이 점수는 <span style={{ color: C.emerald }}>이런 뉴스들</span>에서 나왔어요 😊
        </h2>
        <p className="text-inkMuted text-sm sm:text-[15px] mt-2.5 leading-relaxed max-w-[44ch]">
          최근 반도체 뉴스를 하나하나 읽고 분위기를 모아봤어요. 어떤 기사들이 점수를 만들었는지 직접
          확인해보세요.
        </p>
        <div className="flex flex-wrap items-center gap-2.5 mt-5">
          <span
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
            style={{ background: mood.tint, border: `1px solid ${mood.color}33` }}
          >
            <span className="text-base">{mood.emoji}</span>
            <span className="font-bold text-sm" style={{ color: mood.color }}>
              종합 분위기 · {mood.label} {sentiScore != null ? sentiFmt(sentiScore) : "집계 중"}
            </span>
          </span>
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full" style={{ background: "#EFF3F9" }}>
            <span className="text-base">📑</span>
            <span className="font-semibold text-sm text-inkMuted">
              분석한 기사 <b className="text-ink tnum">{analyzedCount ?? "–"}</b>건
            </span>
          </span>
        </div>
      </div>
    </section>
  );
}
