/** option-c 대시보드 뷰모델 타입 (어댑터 출력). 컴포넌트는 이 타입만 소비한다. */

import type { SignalType, SentimentDirection } from "./tokens";

export interface TickerOption {
  ticker: string;
  name: string;
  /** 종목명 첫 글자(들)로 생성한 로고 이니셜 */
  logo: string;
  /** 데이터 준비 완료 여부(is_active) */
  ready: boolean;
}

export interface HeaderView {
  ticker: string;
  name: string;
  logo: string;
  /** "78,500" 포맷 — null이면 "—" */
  price: string;
  change: {
    dir: "▲" | "▼" | "—";
    amount: string;
    pct: string;
    tone: "up" | "down" | "flat";
  } | null;
}

export interface HeadlineView {
  lead: string;
  accent: string;
  tail: string;
  accentColor: "emerald" | "rose" | "amber" | "muted";
  sub: string;
  badge: {
    dotColor: string;
    text: string;
    textColor: string;
    tint: string;
    meta: string;
  };
}

export interface ReasonCard {
  emoji: string;
  tint: string;
  accent: string;
  title: string;
  desc: string;
  stat: string;
  statLabel: string;
}

export interface GapCompareView {
  /** 0~100 막대 길이 (분위기) */
  sentiPct: number;
  /** 종합 분위기 점수(표시값) — null이면 비표시 */
  sentiScore: number | null;
  /** 0~100 적정가 위치 */
  pricePct: number | null;
  expensive: boolean;
  verdict: { color: string; tint: string; text: string };
}

export interface CycleView {
  phase: string;
  /** 0~100 */
  score: number;
}

export interface HorizonRow {
  when: string;
  sub: string;
  signal: SignalType | null;
}

export interface ChartPoint {
  /** 0-based index */
  idx: number;
  value: number;
}

export interface ChartMarker {
  idx: number;
  signal: SignalType;
  short: string;
  tip: string;
}

export interface ChartView {
  priceTrend: number[];
  markers: ChartMarker[];
  /** 거래일 수 라벨 */
  barCount: number;
}

export interface EvidenceBadge {
  text: string;
  color: string;
  tint: string;
}
export interface EvidenceSection {
  emoji: string;
  title: string;
  badge: EvidenceBadge | null;
  lead: string;
  body: string[];
}

export interface FinanceCard {
  emoji: string;
  tint: string;
  accent: string;
  label: string;
  value: string;
  easy: string;
}

export interface FinanceBandView {
  low: number;
  high: number;
  current: number;
  pos: number;
}

export interface NewsArticleView {
  title: string;
  summary: string;
  source: string;
  url: string;
  when: string;
  sentiment: SentimentDirection;
  keywords: string[];
}

export interface NewsView {
  analyzedCount: number | null;
  sentiScore: number | null;
  articles: NewsArticleView[];
}

export interface AiReasoning {
  horizon: "short" | "mid" | "long";
  label: string;
  text: string;
}

/** 종목 스냅샷 전체 뷰모델 */
export interface DashboardView {
  ready: boolean;
  header: HeaderView;
  /** 분위기 종합 점수(±N) — null 가능 */
  sentiScore: number | null;
  /** 적정가 위치 %(0~100) — null 가능 */
  bandPos: number | null;
  expensive: boolean;
  midSignal: SignalType | null;
  headline: HeadlineView | null;
  reasonCards: ReasonCard[];
  gap: GapCompareView | null;
  cycle: CycleView | null;
  horizons: HorizonRow[];
  chart: ChartView | null;
  evidence: EvidenceSection[];
  /** non-fallback AI 근거. 비어있으면 섹션 미표시(fallback/미생성 제외됨) */
  aiReasonings: AiReasoning[];
  financeCards: FinanceCard[];
  financeBand: FinanceBandView | null;
  financeName: string;
  /** DART 검색 URL (종목명 쿼리) */
  dartUrl: string;
}
