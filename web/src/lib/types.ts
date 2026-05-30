/**
 * Semi Senti — 공유 타입 정의 (PRD v1.2 DashboardSnapshot 미러)
 */

export type SignalType = "BUY" | "SELL" | "HOLD";
export type Perspective = "short" | "mid" | "long";

export interface StockMeta {
  stock_code: string;
  name: string;
  market: string;
}

export interface PriceInfo {
  close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  record_date: string;
  band_low: number | null;
  band_high: number | null;
  band_pos_pct: number | null;
}

export interface FinancialInfo {
  revenue: number | null;
  operating_profit: number | null;
  per: number | null;
  pbr: number | null;
  eps: number | null;
}

export interface SentimentInfo {
  score: number | null;
  raw_score: number | null;
  news_count: number | null;
  score_date: string;
  top_keywords: KeywordEntry[] | null;
}

export interface KeywordEntry {
  word: string;
  weight: number;
  count?: number;
  contribution?: number;
}

export interface SignalInfo {
  perspective: string;
  signal_type: SignalType;
  score: number;
  price: number | null;
  band_low: number | null;
  band_high: number | null;
  sentiment_score: number | null;
  rationale: string;
  signaled_at: string;
}

export interface ReasoningInfo {
  reasoning: string;
  is_fallback: boolean;
  model_version: string | null;
  generated_at?: string;
}

export interface CycleInfo {
  cycle_score: number;
  phase: string;
  inventory_turnover: number | null;
  revenue_growth_pct: number | null;
  op_margin_pct: number | null;
  score_date: string;
}

export interface ChartSummary {
  first_date: string | null;
  last_date: string | null;
  bar_count: number;
}

export interface DashboardSnapshot {
  stock: StockMeta;
  price: PriceInfo;
  financials: FinancialInfo;
  sentiment: SentimentInfo;
  signals: {
    short: SignalInfo | null;
    mid: SignalInfo | null;
    long: SignalInfo | null;
  };
  reasonings: {
    short: ReasoningInfo | null;
    mid: ReasoningInfo | null;
    long: ReasoningInfo | null;
  };
  cycle: CycleInfo | null;
  chart_summary: ChartSummary | null;
}

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartCandles {
  stock_code: string;
  interval: string;
  source: string;
  candles: CandleData[];
  count: number;
  first_date: string | null;
  last_date: string | null;
}
