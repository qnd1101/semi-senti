import type { SentimentBucket } from "@/lib/types";

/**
 * `data_provider.classify_sentiment` 포팅 (T-052).
 * UC-03: -100~-34 공포 / -33~+33 중립 / +34~+100 탐욕
 */
const THRESHOLDS: ReadonlyArray<{ max: number; key: SentimentBucket; labelKo: string }> =
  [
    { max: -34, key: "FEAR", labelKo: "공포" },
    { max: 33, key: "NEUTRAL", labelKo: "중립" },
    { max: 100, key: "GREED", labelKo: "탐욕" },
  ];

export interface SentimentClassification {
  key: SentimentBucket;
  label_ko: string;
}

export function classifySentiment(
  score: number | null | undefined
): SentimentClassification {
  if (score === null || score === undefined) {
    return { key: "UNKNOWN", label_ko: "데이터 없음" };
  }
  const n = Number(score);
  if (Number.isNaN(n)) {
    return { key: "UNKNOWN", label_ko: "데이터 없음" };
  }
  const s = Math.max(-100, Math.min(100, n));
  for (const t of THRESHOLDS) {
    if (s <= t.max) {
      return { key: t.key, label_ko: t.labelKo };
    }
  }
  return { key: "NEUTRAL", label_ko: "중립" };
}
