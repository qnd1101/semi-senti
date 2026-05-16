/**
 * Semi Senti — Frontend DTO.
 *
 * `src/semi_senti/dashboard/data_provider.py` 의 ``DashboardSnapshot`` 과
 * 1:1 미러링한다. 백엔드 어댑터(REST 또는 Route Handler) 가 어떤 방식으로
 * 데이터를 만들어내든 UI 컴포넌트는 이 타입만 알면 충분하다.
 *
 * 백엔드 매핑
 * -----------
 *  Stocks            ↔ Stock
 *  Financials        ↔ Financial / Band
 *  News(+sentiment)  ↔ SentimentSnapshot
 *  Signals           ↔ SignalMarker
 *  cycle_scores      ↔ CycleScore
 */

export type SignalKind = "BUY" | "SELL" | "HOLD";
export type DivergenceKind = "BULLISH" | "BEARISH";
export type SentimentBucket = "FEAR" | "NEUTRAL" | "GREED" | "UNKNOWN";

export interface Stock {
  stock_code: string;
  name: string;
  market: string | null;
  is_active: boolean;
}

export interface Candle {
  /** ISO date 'YYYY-MM-DD' */
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface Band {
  /** 펀더멘털 적정가 상단 (PRD §F-3.1) */
  band_high: number | null;
  /** 펀더멘털 적정가 하단 */
  band_low: number | null;
  method?: string | null;
}

export interface SignalMarker {
  /** ISO datetime */
  time: string;
  kind: SignalKind;
  price: number | null;
  /** 시그널 산출 근거 — 마커 popover에 표시 (PRD §F-3.2.2) */
  reason: string;
  /** UI 색상 키 ('signal.buy' / 'signal.sell' / 'signal.hold') */
  color_token?: string;
  /** 그 시점 감성 점수 (디테일 표시용) */
  sentiment_score?: number | null;
}

export interface DivergenceMarker {
  time: string;
  kind: DivergenceKind;
  reason: string;
  price?: number | null;
}

export interface KeywordContribution {
  keyword: string;
  weight: number;
  count: number;
}

export interface SentimentSnapshot {
  /** -100 ~ +100 */
  score: number | null;
  bucket: SentimentBucket;
  bucket_label_ko: string;
  /** 최근 N일 시계열 (게이지 하단 sparkline 용) */
  history?: Array<{ date: string; score: number }>;
  top_keywords?: KeywordContribution[];
  /** 마지막 분석 시각 ISO */
  updated_at?: string | null;
}

export interface FinancialSummaryDTO {
  current_price: number | null;
  currency: string;
  record_date: string | null;
  revenue: number | null;
  operating_income: number | null;
  per: number | null;
  pbr: number | null;
  eps: number | null;
}

export interface CycleScore {
  /** 0 ~ 100 — 사이클 위치 */
  score: number | null;
  label: string;
  inventory_turnover?: number | null;
  yoy_revenue?: number | null;
  updated_at?: string | null;
}

export interface StaleStatus {
  is_stale: boolean;
  last_updated: string | null;
  hours_old: number | null;
  message: string;
}

/** Python `DashboardSnapshot` 1:1 미러. */
export interface DashboardSnapshot {
  stock_code: string;
  stock_name: string;
  candles: Candle[];
  signals: SignalMarker[];
  divergences: DivergenceMarker[];
  sentiment: SentimentSnapshot;
  financial: FinancialSummaryDTO;
  band: Band;
  cycle?: CycleScore | null;
  stale: StaleStatus;
  generated_at: string;
}
