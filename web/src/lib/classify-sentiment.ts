/**
 * 감성 점수 → 레이블/색상 분류 (PRD §F-4.2.2: 공포/중립/탐욕 3단계)
 */

export type SentimentLabel = "극단 공포" | "공포" | "중립" | "탐욕" | "극단 탐욕";
export type SignalColor = "emerald" | "rose" | "zinc" | "amber";

export function classifySentiment(score: number | null): {
  label: SentimentLabel;
  color: string;
  tailwind: string;
} {
  if (score === null || score === undefined)
    return { label: "중립", color: "#71717a", tailwind: "text-zinc-400" };
  if (score <= -60) return { label: "극단 공포", color: "#f43f5e", tailwind: "text-rose-400" };
  if (score <= -20) return { label: "공포", color: "#fb923c", tailwind: "text-orange-400" };
  if (score < 20) return { label: "중립", color: "#71717a", tailwind: "text-zinc-400" };
  if (score < 60) return { label: "탐욕", color: "#4ade80", tailwind: "text-emerald-400" };
  return { label: "극단 탐욕", color: "#22c55e", tailwind: "text-emerald-500" };
}

export function signalColor(type: string | null | undefined): SignalColor {
  if (type === "BUY") return "emerald";
  if (type === "SELL") return "rose";
  return "zinc";
}

export function signalTailwind(type: string | null | undefined): string {
  if (type === "BUY") return "text-emerald-400 bg-emerald-400/10 border-emerald-400/30";
  if (type === "SELL") return "text-rose-400 bg-rose-400/10 border-rose-400/30";
  return "text-zinc-400 bg-zinc-400/10 border-zinc-400/30";
}

export function formatNumber(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("ko-KR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatPercent(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}%`;
}
