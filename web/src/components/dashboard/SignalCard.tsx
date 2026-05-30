"use client";

import { signalTailwind } from "@/lib/classify-sentiment";
import type { ReasoningInfo, SignalInfo } from "@/lib/types";
import { useState } from "react";

const PERSPECTIVE_LABEL: Record<string, string> = {
  SHORT: "단기 (1일~2주)",
  MID: "중기 (2주~3개월)",
  LONG: "장기 (3개월~)",
};

interface Props {
  perspective: string;
  signal: SignalInfo | null;
  reasoning: ReasoningInfo | null;
}

export function SignalCard({ perspective, signal, reasoning }: Props) {
  const [showReason, setShowReason] = useState(false);
  const type = signal?.signal_type || "HOLD";
  const label = PERSPECTIVE_LABEL[perspective.toUpperCase()] || perspective;

  return (
    <div className="glass-card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400">{label}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${signalTailwind(type)}`}>
          {type}
        </span>
      </div>

      {signal ? (
        <>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tabular-nums">
              {signal.score >= 0 ? "+" : ""}{signal.score.toFixed(1)}
            </span>
            <span className="text-xs text-zinc-500">점수</span>
          </div>
          <div className="text-xs text-zinc-500 truncate" title={signal.rationale}>
            {signal.rationale}
          </div>
          <button
            className="text-xs text-zinc-400 hover:text-zinc-200 text-left underline underline-offset-2"
            onClick={() => setShowReason((v) => !v)}
          >
            {showReason ? "근거 닫기" : "근거 보기 ▸"}
          </button>
          {showReason && reasoning && (
            <div className={`text-xs p-3 rounded-lg bg-zinc-800/60 border border-zinc-700/50 leading-relaxed`}>
              {reasoning.is_fallback && (
                <span className="inline-block mb-1 px-1.5 py-0.5 text-[10px] border border-amber-400/30 text-amber-400 rounded">
                  규칙 기반 근거
                </span>
              )}
              <p className="text-zinc-300">{reasoning.reasoning}</p>
            </div>
          )}
          {showReason && !reasoning && (
            <p className="text-xs text-zinc-500">근거 데이터 없음 (분석 실행 후 표시)</p>
          )}
        </>
      ) : (
        <p className="text-xs text-zinc-500">분석 데이터 없음</p>
      )}
    </div>
  );
}
