"use client";

import { classifySentiment } from "@/lib/classify-sentiment";
import type { SentimentInfo } from "@/lib/types";

interface Props {
  sentiment: SentimentInfo;
}

export function SentimentGauge({ sentiment }: Props) {
  const score = sentiment.score ?? 0;
  const { label, color } = classifySentiment(score);

  // SVG 반원 게이지 (180도)
  const radius = 60;
  const cx = 80;
  const cy = 80;
  const startAngle = -180;
  const endAngle = 0;
  const angle = startAngle + ((score + 100) / 200) * (endAngle - startAngle);

  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const needleX = cx + radius * Math.cos(toRad(angle));
  const needleY = cy + radius * Math.sin(toRad(angle));

  // 배경 호 (공포 → 중립 → 탐욕)
  const arcPath = (from: number, to: number, r: number) => {
    const x1 = cx + r * Math.cos(toRad(from));
    const y1 = cy + r * Math.sin(toRad(from));
    const x2 = cx + r * Math.cos(toRad(to));
    const y2 = cy + r * Math.sin(toRad(to));
    const largeArc = Math.abs(to - from) > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  return (
    <div className="flex flex-col items-center">
      <svg width={160} height={90} viewBox="0 0 160 90">
        {/* 공포 */}
        <path d={arcPath(-180, -120, radius)} fill="none" stroke="#f43f5e" strokeWidth={10} strokeLinecap="round" />
        {/* 중립 */}
        <path d={arcPath(-120, -60, radius)} fill="none" stroke="#71717a" strokeWidth={10} />
        {/* 탐욕 */}
        <path d={arcPath(-60, 0, radius)} fill="none" stroke="#22c55e" strokeWidth={10} strokeLinecap="round" />
        {/* 바늘 */}
        <line
          x1={cx}
          y1={cy}
          x2={needleX}
          y2={needleY}
          stroke={color}
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={5} fill={color} />
      </svg>
      <span className="text-2xl font-bold tabular-nums" style={{ color }}>
        {score >= 0 ? "+" : ""}{score.toFixed(1)}
      </span>
      <span className="text-xs text-zinc-400 mt-0.5">{label}</span>
      <span className="text-xs text-zinc-500 mt-0.5">뉴스 {sentiment.news_count ?? 0}건 · {sentiment.score_date || "—"}</span>
    </div>
  );
}
