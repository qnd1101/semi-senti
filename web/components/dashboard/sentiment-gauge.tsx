"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { SentimentSnapshot } from "@/lib/types";

interface SentimentGaugeProps {
  sentiment: SentimentSnapshot;
  className?: string;
}

const ARC_RADIUS = 42;
const ARC_STROKE = 8;
const CENTER_X = 50;
const CENTER_Y = 50;

function describeArc(startAngle: number, endAngle: number): string {
  const start = polarToCartesian(CENTER_X, CENTER_Y, ARC_RADIUS, endAngle);
  const end = polarToCartesian(CENTER_X, CENTER_Y, ARC_RADIUS, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${ARC_RADIUS} ${ARC_RADIUS} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angleDeg: number
) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function scoreToAngle(score: number): number {
  const clamped = Math.max(-100, Math.min(100, score));
  return ((clamped + 100) / 200) * 180;
}

const MESSAGES = {
  fear: "공포",
  neutral: "중립",
  greed: "탐욕",
} as const;

export function SentimentGauge({ sentiment, className }: SentimentGaugeProps) {
  const score = sentiment.score;
  const needle = score != null ? scoreToAngle(score) : 90;

  const needleEnd = polarToCartesian(CENTER_X, CENTER_Y, ARC_RADIUS - 4, needle);

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <svg viewBox="0 0 100 58" className="h-24 w-full max-w-[200px]">
        {/* Background arc */}
        <path
          d={describeArc(0, 180)}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={ARC_STROKE}
          strokeLinecap="round"
        />
        {/* Fear segment (0-60°) */}
        <path
          d={describeArc(0, 60)}
          fill="none"
          stroke="hsl(var(--signal-sell))"
          strokeWidth={ARC_STROKE}
          strokeLinecap="round"
          opacity={0.7}
        />
        {/* Neutral segment (60-120°) */}
        <path
          d={describeArc(60, 120)}
          fill="none"
          stroke="hsl(var(--signal-hold))"
          strokeWidth={ARC_STROKE}
          strokeLinecap="round"
          opacity={0.7}
        />
        {/* Greed segment (120-180°) */}
        <path
          d={describeArc(120, 180)}
          fill="none"
          stroke="hsl(var(--signal-buy))"
          strokeWidth={ARC_STROKE}
          strokeLinecap="round"
          opacity={0.7}
        />
        {/* Needle */}
        {score != null && (
          <line
            x1={CENTER_X}
            y1={CENTER_Y}
            x2={needleEnd.x}
            y2={needleEnd.y}
            stroke="hsl(var(--foreground))"
            strokeWidth={2}
            strokeLinecap="round"
          />
        )}
        {/* Center dot */}
        <circle
          cx={CENTER_X}
          cy={CENTER_Y}
          r={3}
          fill="hsl(var(--foreground))"
        />
        {/* Labels */}
        <text x={8} y={56} fontSize={5} fill="hsl(var(--muted-foreground))">
          {MESSAGES.fear}
        </text>
        <text
          x={CENTER_X}
          y={56}
          fontSize={5}
          textAnchor="middle"
          fill="hsl(var(--muted-foreground))"
        >
          {MESSAGES.neutral}
        </text>
        <text
          x={92}
          y={56}
          fontSize={5}
          textAnchor="end"
          fill="hsl(var(--muted-foreground))"
        >
          {MESSAGES.greed}
        </text>
      </svg>

      {/* Score + Label */}
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "text-2xl font-bold tabular-nums",
            sentiment.bucket === "GREED" && "text-signal-buy",
            sentiment.bucket === "FEAR" && "text-signal-sell",
            sentiment.bucket === "NEUTRAL" && "text-signal-hold"
          )}
        >
          {score ?? "-"}
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-semibold",
            sentiment.bucket === "GREED" && "bg-signal-buy/20 text-signal-buy",
            sentiment.bucket === "FEAR" && "bg-signal-sell/20 text-signal-sell",
            sentiment.bucket === "NEUTRAL" && "bg-signal-hold/20 text-signal-hold"
          )}
        >
          {sentiment.bucket_label_ko}
        </span>
      </div>
    </div>
  );
}
