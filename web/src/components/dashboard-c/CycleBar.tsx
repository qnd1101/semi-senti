import { C, CYCLE_STAGES } from "@/lib/dashboard-c/tokens";
import type { CycleView } from "@/lib/dashboard-c/types";

export function CycleBar({ cycle }: { cycle: CycleView | null }) {
  return (
    <section className="rise d4 card px-6 sm:px-8 py-7 mb-5">
      <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
        <span className="text-xl">🌡️</span> 지금 반도체 경기는?
      </h2>
      <p className="text-inkMuted text-sm mb-6">
        개별 종목과 별개로, 반도체 산업 전체가 지금 어느 계절에 있는지 보여드려요.
      </p>
      {cycle ? (
        <CycleBody cycle={cycle} />
      ) : (
        <p className="text-faint text-sm py-4">업황 사이클을 집계하고 있어요.</p>
      )}
    </section>
  );
}

function CycleBody({ cycle }: { cycle: CycleView }) {
  const curIdx = Math.max(0, CYCLE_STAGES.findIndex((s) => s.key === cycle.phase));
  const cur = CYCLE_STAGES[curIdx];
  const markPct = Math.max(4, Math.min(96, cycle.score));

  return (
    <div>
      {/* 단계 라벨 */}
      <div className="flex items-stretch mb-3">
        {CYCLE_STAGES.map((s, i) => {
          const on = i === curIdx;
          return (
            <div key={s.key} className="flex-1 flex flex-col items-center gap-1.5 text-center">
              <div className={`text-[18px] leading-none ${on ? "" : "opacity-40 grayscale"}`}>{s.emoji}</div>
              <div className="text-[11px] font-bold leading-tight" style={{ color: on ? s.color : C.faint }}>
                {s.label}
              </div>
              <div className="text-[10px] leading-tight" style={{ color: on ? C.muted : C.faint }}>
                {s.sub}
              </div>
            </div>
          );
        })}
      </div>
      {/* 진행 트랙 + 마커 */}
      <div
        className="relative h-3.5 rounded-full overflow-visible"
        style={{
          background: `linear-gradient(90deg, ${C.roseTint}, ${C.amberTint}, ${C.emeraldTint}, ${C.amberTint}, ${C.roseTint})`,
        }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full grow-x"
          style={{
            width: `${markPct}%`,
            background: `linear-gradient(90deg, ${C.amberSoft}, ${cur.color})`,
            opacity: 0.65,
            transformOrigin: "left",
          }}
        />
        <div className="absolute top-1/2 z-10" style={{ left: `${markPct}%`, transform: "translate(-50%,-50%)" }}>
          <div
            className="w-5 h-5 rounded-full border-[3px] border-white grid place-items-center"
            style={{ background: cur.color, boxShadow: `0 4px 12px -2px ${cur.color}99` }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
          </div>
        </div>
      </div>
      {/* 안내 문구 */}
      <div className="flex items-start gap-2.5 mt-5 rounded-2xl px-4 py-3.5" style={{ background: `${C.emeraldTint}80` }}>
        <span className="text-xl shrink-0">{cur.emoji}</span>
        <p className="text-[13.5px] leading-relaxed text-ink">
          지금은 반도체 경기가 <b>{cur.label}</b>
          {cur.key === "EARLY_CYCLE"
            ? " 하는 단계예요. 장기 투자엔 나쁘지 않은 시점이에요. 🌱"
            : " 구간이에요."}
        </p>
      </div>
    </div>
  );
}
