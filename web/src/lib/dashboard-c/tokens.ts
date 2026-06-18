/**
 * option-c 시안 색/상수 토큰 (인라인 SVG·동적 색용).
 * Tailwind 클래스로 표현 못 하는 동적 색은 이 상수를 style 객체로 쓴다.
 */

export const C = {
  emerald: "#0E9F6E",
  emeraldSoft: "#34D399",
  emeraldTint: "#E7F7F0",
  rose: "#E5484D",
  roseSoft: "#F87171",
  roseTint: "#FDECEC",
  amber: "#C2820B",
  amberSoft: "#F5B544",
  amberTint: "#FCF3E0",
  ink: "#1A2B45",
  muted: "#5A6B85",
  faint: "#9AA8BE",
  line: "#EBF0F7",
  track: "#EFF3F9",
  white: "#FFFFFF",
} as const;

export type SignalType = "BUY" | "SELL" | "HOLD";
export type SentimentDirection = "positive" | "negative" | "neutral";

/** 가격 등락 톤 */
export const TONE: Record<"up" | "down" | "flat", string> = {
  up: C.emerald,
  down: C.rose,
  flat: C.muted,
};

/** 차트 시그널 마커 스타일 (매수 emerald / 매도 rose / 관망 amber) */
export const MARKER_STYLE: Record<SignalType, { color: string; glow: string; arrow: string }> = {
  BUY: { color: C.emerald, glow: "rgba(14,159,110,0.45)", arrow: "⬆" },
  SELL: { color: C.rose, glow: "rgba(229,72,77,0.45)", arrow: "⬇" },
  HOLD: { color: C.amber, glow: "rgba(245,181,68,0.5)", arrow: "⬌" },
};

/** 감성 방향 태그 (숫자 없음 — 방향만; 영업비밀 보호) */
export const SENTI: Record<SentimentDirection, { label: string; emoji: string; color: string; tint: string }> = {
  positive: { label: "긍정", emoji: "😊", color: C.emerald, tint: C.emeraldTint },
  negative: { label: "부정", emoji: "😟", color: C.rose, tint: C.roseTint },
  neutral: { label: "중립", emoji: "😐", color: C.muted, tint: C.track },
};

/**
 * 출처 raw 값(naver_news/google_rss 등) → 한글 라벨.
 * 매핑에 없는 값은 원문을 그대로 유지한다.
 */
export const SOURCE_LABEL: Record<string, string> = {
  naver_news: "네이버뉴스",
  google_rss: "구글뉴스",
};
export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

/** 출처 배지 색/아이콘 (한글 라벨 기준). */
export interface SourceStyle {
  emoji: string;
  color: string;
  tint: string;
}
export function sourceStyle(label: string): SourceStyle {
  if (label.includes("네이버")) return { emoji: "🟢", color: C.emerald, tint: C.emeraldTint };
  if (label.includes("구글")) return { emoji: "🔵", color: "#2563EB", tint: "#E8EFFD" };
  return { emoji: "📰", color: C.muted, tint: C.track };
}

/** 업황 사이클 5단계 */
export interface CycleStage {
  key: string;
  emoji: string;
  label: string;
  sub: string;
  color: string;
}
export const CYCLE_STAGES: CycleStage[] = [
  { key: "BOTTOM", emoji: "❄️", label: "바닥", sub: "불황", color: C.rose },
  { key: "EARLY_CYCLE", emoji: "🌱", label: "회복 초입", sub: "바닥 통과", color: C.amber },
  { key: "MID_CYCLE", emoji: "☀️", label: "상승", sub: "호황", color: C.emerald },
  { key: "PEAK", emoji: "🔥", label: "고점", sub: "과열", color: C.amber },
  { key: "DOWN", emoji: "🍂", label: "하락", sub: "둔화", color: C.rose },
];

/** 신호 한국어 라벨 */
export const SIG_KO: Record<SignalType, string> = {
  BUY: "사기(BUY)",
  HOLD: "관망(HOLD)",
  SELL: "팔기(SELL)",
};

/**
 * 분위기 무드: 점수 부호/세기에 따라 "따뜻함/미지근함/차가움" 라벨·톤을 산출한다.
 * - 양수(우호적) → 따뜻함(긍정), 음수(부정적) → 차가움(부정), 0 근처 → 미지근함(중립).
 * - 점수 '값'은 표시 OK(PRD 표시값)이나, 경계 계수는 라벨로만 노출(영업비밀 보호).
 * 입문자 톤(다정한 존댓말)에 맞춘 온도계 메타포 라벨을 돌려준다.
 */
export interface SentimentMood {
  /** 온도계 메타포 라벨 (따뜻함/미지근함/차가움) */
  label: string;
  /** 방향 (긍정/중립/부정) */
  dir: SentimentDirection;
  emoji: string;
  color: string;
  tint: string;
  /** 우호적(따뜻한) 분위기 여부 — 카피 분기용 */
  warm: boolean;
  /** 부정적(차가운) 분위기 여부 — 카피 분기용 */
  cold: boolean;
}

// 중립으로 간주할 경계(±). UI 텍스트로 직접 노출하지 않는다.
const MOOD_NEUTRAL_BAND = 10;

export function sentimentMood(score: number | null): SentimentMood {
  if (score == null || Math.abs(score) < MOOD_NEUTRAL_BAND) {
    return {
      label: "미지근함",
      dir: "neutral",
      emoji: SENTI.neutral.emoji,
      color: SENTI.neutral.color,
      tint: SENTI.neutral.tint,
      warm: false,
      cold: false,
    };
  }
  if (score > 0) {
    return {
      label: "따뜻함",
      dir: "positive",
      emoji: SENTI.positive.emoji,
      color: SENTI.positive.color,
      tint: SENTI.positive.tint,
      warm: true,
      cold: false,
    };
  }
  return {
    label: "차가움",
    dir: "negative",
    emoji: SENTI.negative.emoji,
    color: SENTI.negative.color,
    tint: SENTI.negative.tint,
    warm: false,
    cold: true,
  };
}
