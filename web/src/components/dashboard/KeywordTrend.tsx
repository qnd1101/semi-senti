"use client";

import type { KeywordEntry } from "@/lib/types";

interface Props {
  keywords: KeywordEntry[] | null | undefined;
  limit?: number;
}

export function KeywordTrend({ keywords, limit = 8 }: Props) {
  const list = (keywords || []).slice(0, limit);
  if (!list.length)
    return <p className="text-xs text-zinc-500">키워드 데이터 없음</p>;

  return (
    <div className="flex flex-wrap gap-1.5">
      {list.map((kw, i) => {
        const positive = kw.weight > 0;
        return (
          <span
            key={i}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border
              ${positive ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/30" : "text-rose-400 bg-rose-400/10 border-rose-400/30"}`}
          >
            {positive ? "↑" : "↓"} {kw.word}
          </span>
        );
      })}
    </div>
  );
}
